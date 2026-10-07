"""The agent loop.

One step = one model call. Each step:
  1. send the conversation and tool specs to the model;
  2. if it asks for tools, run each one and append the results;
  3. if it answers in plain text, stop.
A hard step limit stops runaway loops.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from agentloop.llm.base import LLMClient, LLMError, Message, ToolCall, Usage
from agentloop.tools.base import Tool, ToolResult

Event = dict[str, Any]
Observer = Callable[[Event], None]
Status = Literal["answered", "step_limit", "llm_error"]


@dataclass
class RunResult:
    status: Status
    answer: str
    steps: int
    usage: Usage
    messages: list[Message] = field(default_factory=list)


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        tools: list[Tool],
        system_prompt: str,
        max_steps: int = 25,
        observers: list[Observer] | None = None,
    ):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.observers = observers or []

    def emit(self, event: Event) -> None:
        for observer in self.observers:
            observer(event)

    def run(self, task: str) -> RunResult:
        messages = [Message("system", self.system_prompt), Message("user", task)]
        specs = [t.spec() for t in self.tools.values()]
        usage = Usage()
        self.emit({"type": "start", "task": task, "model": self.llm.model, "max_steps": self.max_steps})

        for step in range(1, self.max_steps + 1):
            started = time.monotonic()
            try:
                response = self.llm.chat(messages, specs)
            except LLMError as exc:
                return self._finish(messages, "llm_error", str(exc), step - 1, usage)
            usage += response.usage
            messages.append(response.to_message())
            self.emit({
                "type": "model",
                "step": step,
                "model": self.llm.model,
                "text": response.text,
                "tool_calls": [tc.name for tc in response.tool_calls],
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "seconds": round(time.monotonic() - started, 2),
            })

            if not response.tool_calls:
                return self._finish(messages, "answered", response.text, step, usage)

            for call in response.tool_calls:
                result = self.execute(call)
                self.emit({
                    "type": "tool",
                    "step": step,
                    "tool": call.name,
                    "arguments": call.arguments,
                    "ok": result.ok,
                    "result_chars": len(result.output),
                    "truncated": result.truncated,
                    "preview": result.output[:300],
                })
                messages.append(
                    Message("tool", result.output, tool_call_id=call.id, name=call.name)
                )

        return self._finish(
            messages,
            "step_limit",
            f"Stopped after reaching the step limit ({self.max_steps}) without a final answer.",
            self.max_steps,
            usage,
        )

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.tools.get(call.name)
        if tool is None:
            available = ", ".join(sorted(self.tools))
            return ToolResult.error(f"unknown tool '{call.name}'; available tools: {available}")
        return tool(call.arguments)

    def _finish(self, messages, status: Status, answer: str, steps: int, usage: Usage) -> RunResult:
        self.emit({
            "type": "end",
            "status": status,
            "answer": answer,
            "steps": steps,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        })
        return RunResult(status, answer, steps, usage, messages)
