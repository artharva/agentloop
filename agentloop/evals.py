"""The evaluation harness behind `agentloop eval`.

Each task folder in evals/tasks/ holds:
  task.md        the instruction given to the agent
  task.json      {"difficulty": "easy" | "medium" | "hard", "allow_test_edits": false}
  repo/          the buggy project with its visible tests (all the agent sees)
  hidden_tests/  extra tests used only for judging, so special-casing the visible tests fails
  solution/      reference fix (files overlaid on repo/), used only to validate the task

A run copies repo/ into a fresh temp folder, commits it to git, runs the agent
with fixed budgets and auto-approval, then copies in the hidden tests and runs
pytest itself. The task passes only if every test passes.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from statistics import mean
from typing import Callable

from agentloop.llm.base import LLMClient
from agentloop.loop import RunResult
from agentloop.pytest_runner import TestReport, run_pytest
from agentloop.runlog import RunLogger
from agentloop.safety import CommandRunner
from agentloop.session import RunOptions, build_agent

DIFFICULTIES = ("easy", "medium", "hard")


@dataclass
class EvalTask:
    id: str
    path: Path
    difficulty: str
    instruction: str
    allow_test_edits: bool = False


@dataclass
class EvalRow:
    version: str
    run: int
    task: str
    difficulty: str
    passed: int
    status: str
    steps: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: int
    invalid_tool_calls: int
    cheating_blocked: int
    loop_detected: int
    seconds: float
    model: str
    failure_reason: str


def discover_tasks(tasks_dir: str | Path, only: list[str] | None = None) -> list[EvalTask]:
    tasks = []
    for folder in sorted(Path(tasks_dir).iterdir()):
        if not (folder / "task.md").is_file():
            continue
        if only and folder.name not in only:
            continue
        meta = json.loads((folder / "task.json").read_text(encoding="utf-8"))
        if meta["difficulty"] not in DIFFICULTIES:
            raise ValueError(f"{folder.name}: unknown difficulty {meta['difficulty']!r}")
        tasks.append(EvalTask(
            id=folder.name,
            path=folder,
            difficulty=meta["difficulty"],
            instruction=(folder / "task.md").read_text(encoding="utf-8").strip(),
            allow_test_edits=meta.get("allow_test_edits", False),
        ))
    return tasks


def prepare_workspace(task: EvalTask, parent: Path) -> Path:
    """Copy the task's repo into parent/repo and commit it, so the run starts clean."""
    repo = parent / "repo"
    shutil.copytree(task.path / "repo", repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    git = ["git", "-c", "user.name=AgentLoop", "-c", "user.email=agentloop@example.invalid", "-c", "core.autocrlf=false"]
    for argv in (["git", "init", "-q"], git + ["add", "-A"], git + ["commit", "-q", "-m", "task start"]):
        subprocess.run(argv, cwd=repo, check=True, capture_output=True)
    return repo


def judge(task: EvalTask, repo: Path, timeout: float = 120) -> TestReport:
    """Add the hidden tests and run the whole suite. The model's opinion is not consulted."""
    hidden = task.path / "hidden_tests"
    if hidden.is_dir():
        for file in hidden.iterdir():
            if file.is_file():
                shutil.copy2(file, repo / file.name)
    return run_pytest(CommandRunner(repo), timeout=timeout)


def failure_reason(result: RunResult | None, report: TestReport, error: str = "") -> str:
    if error:
        return f"crash: {error}"[:200]
    if report.passed:
        return ""
    if result is None:
        return report.summary
    if result.status == "success":
        return f"agent's checks passed but hidden tests failed ({report.summary}); likely fixed the symptom, not the cause"
    reason = {
        "answered": "finished without changing any files",
        "tests_failing": "kept claiming done while tests failed",
        "step_limit": "ran out of steps",
        "token_limit": "ran out of tokens",
        "time_limit": "ran out of time",
        "loop_detected": "repeated the same call without progress",
        "too_many_errors": "too many failed tool calls in a row",
        "llm_error": "model API error",
        "aborted": "run was aborted",
    }.get(result.status, result.status)
    if result.status == "llm_error":
        reason += f": {result.answer[:120]}"
    return f"{reason} ({report.summary})"


def run_task(
    task: EvalTask,
    llm: LLMClient,
    options: RunOptions,
    version: str,
    run: int,
    logs_dir: Path | None = None,
    keep: bool = False,
) -> EvalRow:
    parent = Path(tempfile.mkdtemp(prefix=f"agentloop-{task.id}-"))
    result: RunResult | None = None
    error = ""
    started = time.monotonic()
    try:
        repo = prepare_workspace(task, parent)
        task_options = RunOptions(
            prompt=options.prompt,
            plan_mode=options.plan_mode,
            allow_test_edits=task.allow_test_edits,
            test_timeout=options.test_timeout,
            loop=options.loop,
        )
        observers = [RunLogger(logs_dir, label=f"{version}-r{run}-{task.id}")] if logs_dir else []
        agent = build_agent(repo, llm, task_options, observers=observers)
        try:
            result = agent.run(task.instruction)
        except Exception as exc:  # a crash is a result, not a reason to stop the whole eval
            error = f"{type(exc).__name__}: {exc}"
        report = judge(task, repo, timeout=max(options.test_timeout, 60))
    finally:
        if not keep:
            remove_tree(parent)
    stats = result.stats if result else None
    usage = result.usage if result else None
    return EvalRow(
        version=version,
        run=run,
        task=task.id,
        difficulty=task.difficulty,
        passed=int(report.passed and not error),
        status=result.status if result else "crash",
        steps=result.steps if result else 0,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
        tool_calls=stats.tool_calls if stats else 0,
        invalid_tool_calls=stats.invalid_tool_calls if stats else 0,
        cheating_blocked=stats.cheating_blocked if stats else 0,
        loop_detected=int(stats.loop_detected) if stats else 0,
        seconds=round(result.seconds if result else time.monotonic() - started, 1),
        model=llm.model,
        failure_reason=failure_reason(result, report, error),
    )


def run_eval(
    tasks: list[EvalTask],
    make_llm: Callable[[], LLMClient],
    options: RunOptions,
    version: str,
    repeat: int = 1,
    logs_dir: Path | None = None,
    keep: bool = False,
    on_row: Callable[[EvalRow], None] | None = None,
) -> list[EvalRow]:
    rows = []
    for run in range(1, repeat + 1):
        for task in tasks:
            row = run_task(task, make_llm(), options, version, run, logs_dir, keep)
            rows.append(row)
            if on_row:
                on_row(row)
    return rows


# --- results ---------------------------------------------------------------

def write_csv(rows: list[EvalRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[fl.name for fl in fields(EvalRow)])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def read_csv(path: Path) -> list[EvalRow]:
    types = {fl.name: fl.type for fl in fields(EvalRow)}
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            values = {}
            for key, value in raw.items():
                kind = types[key]
                values[key] = int(value) if kind in (int, "int") else float(value) if kind in (float, "float") else value
            rows.append(EvalRow(**values))
    return rows


def summarize(rows: list[EvalRow]) -> dict[str, float]:
    """The metrics from the spec, averaged over every (run, task) pair."""
    if not rows:
        return {}
    summary = {
        "pass_rate": 100 * mean(r.passed for r in rows),
        "avg_steps": mean(r.steps for r in rows),
        "avg_tokens": mean(r.total_tokens for r in rows),
        "invalid_tool_calls": sum(r.invalid_tool_calls for r in rows),
        "cheating_blocked": sum(r.cheating_blocked for r in rows),
        "loops_detected": sum(r.loop_detected for r in rows),
        "avg_seconds": mean(r.seconds for r in rows),
        "runs": len({r.run for r in rows}),
        "tasks": len({r.task for r in rows}),
    }
    for level in DIFFICULTIES:
        subset = [r.passed for r in rows if r.difficulty == level]
        if subset:
            summary[f"pass_rate_{level}"] = 100 * mean(subset)
    return summary


def failure_log(rows: list[EvalRow]) -> str:
    """A Markdown failure log: one line per failed task, with an auto-detected reason."""
    lines = [
        f"# Failure log: {rows[0].version if rows else ''}",
        "",
        "One line per failed task. The reason is detected automatically; add what you learned in Notes.",
        "",
        "| Run | Task | Difficulty | Status | Why it failed | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        if not r.passed:
            reason = r.failure_reason.replace("|", "/").replace("\n", " ")
            lines.append(f"| {r.run} | {r.task} | {r.difficulty} | {r.status} | {reason} |  |")
    if len(lines) == 6:
        lines.append("| | | | | No failures. | |")
    return "\n".join(lines) + "\n"


def remove_tree(path: Path) -> None:
    """rmtree that also removes read-only files (git objects on Windows)."""

    def make_writable(func, target, _info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    try:
        shutil.rmtree(path, onexc=make_writable)  # Python 3.12+
    except TypeError:
        shutil.rmtree(path, onerror=make_writable)
