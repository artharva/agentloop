"""The agent loop.

One step = one model call. Each step:
  1. check budgets and trim the context if it is getting full;
  2. send the conversation and tool specs to the model;
  3. if it asks for tools, run each one (through the safety layer) and append the results;
  4. if it answers in plain text, verify: when files changed, the tests must pass.
     The model's "I'm done" is not enough; failing tests send it back to work.
The run stops on success, on a budget, on a detected loop, or when the user aborts.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from agentloop.context import ContextManager
from agentloop.llm.base import LLMClient, LLMError, Message, ToolCall, Usage
from agentloop.pytest_runner import TestReport, format_report, run_pytest
from agentloop.tools.base import Tool, ToolContext, ToolResult

Event = dict[str, Any]
Observer = Callable[[Event], None]
Status = Literal[
    "success",  # files changed and the test suite passes (checked by code)
    "answered",  # no files changed; the model gave a plain answer
    "tests_failing",  # the model kept claiming done while tests failed
    "step_limit",
    "token_limit",
    "time_limit",
    "loop_detected",
    "too_many_errors",
    "aborted",  # the user rejected the plan or stopped the run
    "llm_error",
]
Verify = Literal["auto", "always", "never"]


@dataclass
class LoopConfig:
    max_steps: int = 25
    max_tokens: int = 400_000  # input + output, summed over the run
    max_seconds: float = 900
    context_limit: int = 60_000
    # auto: run the tests when files changed. always: also when nothing
    # changed (evals, where the task is always "make the tests pass").
    verify: Verify = "auto"
    max_done_claims: int = 3  # "done" claims rejected by failing tests before giving up
    repeat_limit: int = 3  # identical call, nothing changed in between
    max_consecutive_errors: int = 6


@dataclass
class RunStats:
    tool_calls: int = 0
    invalid_tool_calls: int = 0
    blocked: int = 0
    cheating_blocked: int = 0
    rejected_by_user: int = 0
    tool_errors: int = 0
    trims: int = 0
    done_claims_rejected: int = 0
    loop_detected: bool = False


@dataclass
class RunResult:
    status: Status
    answer: str
    steps: int
    usage: Usage
    stats: RunStats
    changed_files: list[str]
    seconds: float
    final_tests: TestReport | None = None
    messages: list[Message] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.status in ("success", "answered")


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        tools: list[Tool],
        ctx: ToolContext,
        system_prompt: str,
        config: LoopConfig | None = None,
        observers: list[Observer] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.ctx = ctx
        self.system_prompt = system_prompt
        self.config = config or LoopConfig()
        self.observers = observers or []
        self.clock = clock
        self.context = ContextManager(self.config.context_limit)

    def emit(self, event: Event) -> None:
        for observer in self.observers:
            observer(event)

    def run(self, task: str) -> RunResult:
        cfg = self.config
        self.started = self.clock()
        self.messages = [Message("system", self.system_prompt), Message("user", task)]
        self.usage = Usage()
        self.stats = RunStats()
        specs = [t.spec() for t in self.tools.values()]
        seen: Counter[tuple[str, str, int]] = Counter()
        consecutive_errors = 0
        self.emit({"type": "start", "task": task, "model": self.llm.model, "tools": list(self.tools), "config": cfg.__dict__})

        for step in range(1, cfg.max_steps + 1):
            if (stop := self._check_budgets(step - 1)) is not None:
                return stop

            report = self.context.fit(self.messages, specs)
            if report:
                self.stats.trims += 1
                self.emit({"type": "trim", "step": step, "trimmed": report.trimmed,
                           "tokens_before": report.tokens_before, "tokens_after": report.tokens_after})

            t0 = self.clock()
            try:
                response = self.llm.chat(self.messages, specs)
            except LLMError as exc:
                return self._finish("llm_error", str(exc), step - 1)
            self.usage += response.usage
            self.messages.append(response.to_message())
            self.emit({
                "type": "model", "step": step, "model": self.llm.model, "text": response.text,
                "tool_calls": [tc.name for tc in response.tool_calls],
                "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
                "seconds": round(self.clock() - t0, 2),
            })

            if not response.tool_calls:
                outcome = self._on_done_claim(response.text, step)
                if outcome is not None:
                    return outcome
                continue

            for call in response.tool_calls:
                key = (call.name, json.dumps(call.arguments, sort_keys=True), self.ctx.write_version)
                seen[key] += 1
                if seen[key] >= cfg.repeat_limit:
                    self.stats.loop_detected = True
                    return self._finish(
                        "loop_detected",
                        f"Stopped: the agent made the same call {cfg.repeat_limit} times without changing "
                        f"anything in between: {call.name} {call.arguments}",
                        step,
                    )
                result = self.execute(call)
                self._count(result)
                consecutive_errors = 0 if result.ok else consecutive_errors + 1
                self.emit({
                    "type": "tool", "step": step, "tool": call.name, "arguments": call.arguments,
                    "ok": result.ok, "kind": result.kind, "result_chars": len(result.output),
                    "truncated": result.truncated, "preview": result.output[:300],
                })
                self.messages.append(Message(
                    "tool", result.output, tool_call_id=call.id, name=call.name, summary=short_args(call.arguments),
                ))
                if self.ctx.abort_reason:
                    return self._finish("aborted", self.ctx.abort_reason, step)
            if consecutive_errors >= cfg.max_consecutive_errors:
                return self._finish("too_many_errors", f"Stopped after {consecutive_errors} failed tool calls in a row.", step)

        return self._finish("step_limit", f"Stopped: reached the step limit ({cfg.max_steps}).", cfg.max_steps)

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.tools.get(call.name)
        if tool is None:
            available = ", ".join(sorted(self.tools))
            return ToolResult.error(f"unknown tool '{call.name}'; available tools: {available}", kind="invalid")
        return tool(call.arguments)

    # --- helpers -----------------------------------------------------------

    def _on_done_claim(self, text: str, step: int) -> RunResult | None:
        """The model answered in plain text. Decide, in code, whether that ends the run."""
        cfg = self.config
        must_verify = cfg.verify == "always" or (cfg.verify == "auto" and self.ctx.changed_files)
        if not must_verify:
            return self._finish("answered", text, step)
        report = run_pytest(self.ctx.runner, timeout=self.ctx.test_timeout)
        self.emit({"type": "verify", "step": step, "passed": report.passed, "summary": report.summary})
        if report.passed:
            return self._finish("success", text, step, report)
        self.stats.done_claims_rejected += 1
        if self.stats.done_claims_rejected >= cfg.max_done_claims:
            return self._finish("tests_failing", f"Stopped: the tests still fail after {cfg.max_done_claims} attempts to finish.\n{report.summary}", step, report)
        self.messages.append(Message(
            "user",
            "You said you are done, but AgentLoop ran the tests and they do not pass, so the task is "
            f"not finished. Keep working.\n\n{format_report(report, max_lines=60)}",
        ))
        return None

    def _check_budgets(self, steps: int) -> RunResult | None:
        cfg = self.config
        elapsed = self.clock() - self.started
        if elapsed > cfg.max_seconds:
            return self._finish("time_limit", f"Stopped: time budget reached ({cfg.max_seconds:.0f}s).", steps)
        total = self.usage.input_tokens + self.usage.output_tokens
        if total > cfg.max_tokens:
            return self._finish("token_limit", f"Stopped: token budget reached ({total} of {cfg.max_tokens}).", steps)
        return None

    def _count(self, result: ToolResult) -> None:
        s = self.stats
        s.tool_calls += 1
        if result.kind == "invalid":
            s.invalid_tool_calls += 1
        elif result.kind == "blocked":
            s.blocked += 1
        elif result.kind == "cheat_blocked":
            s.cheating_blocked += 1
        elif result.kind == "rejected":
            s.rejected_by_user += 1
        elif result.kind == "error":
            s.tool_errors += 1

    def _finish(self, status: Status, answer: str, steps: int, tests: TestReport | None = None) -> RunResult:
        seconds = round(self.clock() - self.started, 2)
        result = RunResult(
            status=status, answer=answer, steps=steps, usage=self.usage, stats=self.stats,
            changed_files=list(self.ctx.changed_files), seconds=seconds, final_tests=tests, messages=self.messages,
        )
        self.emit({
            "type": "end", "status": status, "answer": answer, "steps": steps, "seconds": seconds,
            "input_tokens": self.usage.input_tokens, "output_tokens": self.usage.output_tokens,
            "changed_files": result.changed_files, "stats": self.stats.__dict__,
            "tests": tests.summary if tests else None,
        })
        return result


def short_args(arguments: dict[str, Any]) -> str:
    """A compact label for a call, used in trimmed-context stubs."""
    for key in ("path", "pattern", "keyword"):
        if arguments.get(key):
            return str(arguments[key])[:60]
    return ""
