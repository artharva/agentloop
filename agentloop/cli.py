"""Command-line interface: `agentloop run`, `agentloop eval`, `agentloop compare`."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from agentloop import __version__
from agentloop.approval import AutoApprover, ConsoleApprover
from agentloop.llm import LLMError, make_client
from agentloop.loop import LoopConfig
from agentloop.runlog import RunLogger
from agentloop.safety import Workspace, git_status
from agentloop.session import DEFAULT_PROMPT, RunOptions, build_agent

app = typer.Typer(add_completion=False, help="AgentLoop: a coding agent built from scratch.")
console = Console()

STATUS_STYLE = {"success": "green", "answered": "green", "step_limit": "yellow", "token_limit": "yellow", "time_limit": "yellow"}


@app.callback()
def main() -> None:
    """AgentLoop: a coding agent built from scratch."""


def console_observer(event: dict) -> None:
    kind = event["type"]
    if kind == "start":
        console.print(f"[bold]Task:[/] {event['task']}  [dim]({event['model']}, max {event['config']['max_steps']} steps)[/]")
    elif kind == "model" and event["tool_calls"] and event["text"]:
        console.print(f"[dim]{event['text']}[/]")
    elif kind == "tool":
        args = json.dumps(event["arguments"], ensure_ascii=False)
        if len(args) > 120:
            args = args[:117] + "..."
        mark = {"ok": "[green]ok[/]", "rejected": "[yellow]rejected[/]"}.get(event["kind"], f"[red]{event['kind']}[/]")
        cut = " [yellow](truncated)[/]" if event["truncated"] else ""
        console.print(f"[cyan]step {event['step']}[/] {event['tool']} {args} -> {mark}{cut}")
        if not event["ok"]:
            console.print(f"  [red]{event['preview'][:300]}[/]")
    elif kind == "verify":
        style = "green" if event["passed"] else "red"
        console.print(f"[{style}]Verification: {event['summary']}[/]")
    elif kind == "trim":
        console.print(f"[dim]Context trimmed: {event['trimmed']} old tool results stubbed ({event['tokens_before']} -> {event['tokens_after']} tokens)[/]")


def loop_config(max_steps: int, max_tokens: int, max_seconds: float, context_limit: int, verify: str = "auto") -> LoopConfig:
    return LoopConfig(max_steps=max_steps, max_tokens=max_tokens, max_seconds=max_seconds, context_limit=context_limit, verify=verify)


@app.command()
def run(
    task: str = typer.Argument(..., help="What you want the agent to do, in plain English."),
    repo: Path = typer.Option(Path("."), "--repo", "-r", help="Path to the project the agent works on."),
    model: str = typer.Option(None, "--model", "-m", envvar="AGENTLOOP_MODEL", help="Model name (default: gemini-flash-latest, falling back to gemini-flash-lite-latest)."),
    prompt: Path = typer.Option(DEFAULT_PROMPT, "--prompt", help="System prompt file."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Approve every file change and the plan without asking."),
    plan: bool = typer.Option(True, "--plan/--no-plan", help="Require an approved plan before any file change."),
    allow_test_edits: bool = typer.Option(False, "--allow-test-edits", help="Let the agent change test files."),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Run even if the repo has uncommitted changes (or no git)."),
    max_steps: int = typer.Option(25, "--max-steps", min=1, help="Hard limit on model calls."),
    max_tokens: int = typer.Option(400_000, "--max-tokens", min=1000, help="Token budget for the whole run."),
    max_seconds: float = typer.Option(900, "--max-seconds", min=10, help="Wall-clock budget in seconds."),
    context_limit: int = typer.Option(60_000, "--context-limit", min=2000, help="Prompt size (tokens) at which old tool output gets trimmed."),
    test_timeout: float = typer.Option(60, "--test-timeout", min=1, help="Seconds before a pytest run is killed."),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir", help="Where to write the JSONL run log."),
) -> None:
    """Run the agent on a task inside a repo."""
    try:
        workspace = Workspace(repo)
    except NotADirectoryError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2)
    if not allow_dirty:
        clean, message = git_status(workspace.root)
        if not clean:
            console.print(f"[red]Refusing to start.[/] {message}")
            raise typer.Exit(2)
    try:
        llm = make_client(model)
    except LLMError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2)

    logger = RunLogger(runs_dir)
    options = RunOptions(
        prompt=prompt, plan_mode=plan, allow_test_edits=allow_test_edits, test_timeout=test_timeout,
        loop=loop_config(max_steps, max_tokens, max_seconds, context_limit),
    )
    approver = AutoApprover() if yes else ConsoleApprover(console)
    agent = build_agent(workspace.root, llm, options, approver=approver, observers=[logger, console_observer])
    result = agent.run(task)

    style = STATUS_STYLE.get(result.status, "red")
    console.print(Panel(Markdown(result.answer or "(no answer)"), title=result.status, border_style=style))
    lines = [f"{result.steps} steps, {result.usage.input_tokens} in / {result.usage.output_tokens} out tokens, {result.seconds:.0f}s."]
    if result.final_tests:
        lines.append(f"Tests (checked by AgentLoop): {result.final_tests.summary}")
    if result.changed_files:
        lines.append("Changed: " + ", ".join(result.changed_files))
        lines.append("Review with `git diff`; undo everything with `git checkout -- .` (and delete any new files).")
    lines.append(f"Log: {logger.path}")
    console.print("[dim]" + "\n".join(lines) + "[/]")
    raise typer.Exit(0 if result.succeeded else 1)


@app.command("eval")
def eval_cmd(
    version: str = typer.Option(..., "--version", "-v", help="Label for this agent version, e.g. v1. Results go to <results-dir>/<version>.csv."),
    tasks_dir: Path = typer.Option(Path("evals/tasks"), "--tasks-dir", help="Folder of benchmark tasks."),
    only: str = typer.Option(None, "--only", help="Comma-separated task ids to run (default: all)."),
    repeat: int = typer.Option(1, "--repeat", min=1, help="Run every task this many times (model output varies)."),
    model: str = typer.Option(None, "--model", "-m", envvar="AGENTLOOP_MODEL", help="Model name. Pin one for comparable results."),
    prompt: Path = typer.Option(DEFAULT_PROMPT, "--prompt", help="System prompt file."),
    plan: bool = typer.Option(True, "--plan/--no-plan", help="Plan mode (plans are auto-approved in evals)."),
    max_steps: int = typer.Option(30, "--max-steps", min=1),
    max_tokens: int = typer.Option(300_000, "--max-tokens", min=1000),
    max_seconds: float = typer.Option(600, "--max-seconds", min=10),
    context_limit: int = typer.Option(60_000, "--context-limit", min=2000),
    test_timeout: float = typer.Option(60, "--test-timeout", min=1),
    min_interval: float = typer.Option(0, "--min-interval", min=0, help="Minimum seconds between model calls (free-tier rate limits)."),
    results_dir: Path = typer.Option(Path("evals/results"), "--results-dir"),
    logs_dir: Path = typer.Option(Path("runs/evals"), "--logs-dir", help="Where per-task JSONL logs go."),
    keep: bool = typer.Option(False, "--keep", help="Keep each task's temp folder for inspection."),
) -> None:
    """Run the benchmark and write one results table for this agent version."""
    from agentloop.evals import discover_tasks, failure_log, run_eval, summarize, write_csv
    from agentloop.llm.throttle import ThrottledClient

    if shutil.which("git") is None:
        console.print("[red]git is required for evals (each task runs in a fresh git repo). Install git and try again.[/]")
        raise typer.Exit(2)
    tasks = discover_tasks(tasks_dir, only.split(",") if only else None)
    if not tasks:
        console.print(f"[red]No tasks found in {tasks_dir}.[/]")
        raise typer.Exit(2)
    try:
        make_client(model)  # fail fast on a missing key
    except LLMError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2)

    def make_llm():
        client = make_client(model)
        return ThrottledClient(client, min_interval) if min_interval else client

    options = RunOptions(prompt=prompt, plan_mode=plan, test_timeout=test_timeout,
                         loop=loop_config(max_steps, max_tokens, max_seconds, context_limit, verify="always"))
    console.print(f"[bold]Eval {version}[/]: {len(tasks)} tasks x {repeat} run(s), prompt {prompt.name}, plan mode {'on' if plan else 'off'}")

    def on_row(row):
        mark = "[green]PASS[/]" if row.passed else "[red]FAIL[/]"
        extra = f" - {row.failure_reason}" if row.failure_reason else ""
        console.print(f"  run {row.run} {row.task:<28} {mark} {row.status:<14} {row.steps:>2} steps {row.total_tokens:>7} tok {row.seconds:>6.0f}s{extra}")

    rows = run_eval(tasks, make_llm, options, version, repeat, logs_dir, keep, on_row)
    csv_path = results_dir / f"{version}.csv"
    write_csv(rows, csv_path)
    (results_dir / f"{version}_failures.md").write_text(failure_log(rows), encoding="utf-8")
    print_summary({version: summarize(rows)})
    console.print(f"[dim]Results: {csv_path}\nFailure log: {results_dir / f'{version}_failures.md'}[/]")


@app.command()
def compare(results: list[Path] = typer.Argument(..., help="Result CSVs to compare, e.g. evals/results/v1.csv evals/results/v2.csv")) -> None:
    """Compare eval results side by side."""
    from agentloop.evals import read_csv, summarize

    summaries = {}
    per_task: dict[str, dict[str, str]] = {}
    for path in results:
        rows = read_csv(path)
        label = rows[0].version if rows else path.stem
        summaries[label] = summarize(rows)
        for row in rows:
            cell = per_task.setdefault(row.task, {}).setdefault(label, "0/0")
            passed, total = map(int, cell.split("/"))
            per_task[row.task][label] = f"{passed + row.passed}/{total + 1}"
    print_summary(summaries)
    table = Table(title="Passes per task")
    table.add_column("task")
    for label in summaries:
        table.add_column(label, justify="right")
    for task in sorted(per_task):
        table.add_row(task, *(per_task[task].get(label, "-") for label in summaries))
    console.print(table)


def print_summary(summaries: dict[str, dict[str, float]]) -> None:
    metrics = [
        ("pass_rate", "Pass rate (%)", "{:.1f}"),
        ("pass_rate_easy", "  easy (%)", "{:.1f}"),
        ("pass_rate_medium", "  medium (%)", "{:.1f}"),
        ("pass_rate_hard", "  hard (%)", "{:.1f}"),
        ("avg_steps", "Avg steps per task", "{:.1f}"),
        ("avg_tokens", "Avg tokens per task", "{:.0f}"),
        ("invalid_tool_calls", "Invalid tool calls", "{:.0f}"),
        ("cheating_blocked", "Cheating attempts blocked", "{:.0f}"),
        ("loops_detected", "Loops detected", "{:.0f}"),
        ("avg_seconds", "Avg seconds per task", "{:.0f}"),
        ("runs", "Runs", "{:.0f}"),
    ]
    table = Table(title="Eval results")
    table.add_column("Metric")
    for label in summaries:
        table.add_column(label, justify="right")
    for key, name, fmt in metrics:
        table.add_row(name, *(fmt.format(s[key]) if key in s else "-" for s in summaries.values()))
    console.print(table)


@app.command()
def version() -> None:
    """Print the AgentLoop version."""
    console.print(__version__)


if __name__ == "__main__":
    app()
