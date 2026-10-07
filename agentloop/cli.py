"""Command-line entry point: `agentloop run "<task>" --repo ./path`."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agentloop import __version__
from agentloop.llm import LLMError, make_client
from agentloop.loop import AgentLoop
from agentloop.runlog import RunLogger
from agentloop.safety import Workspace
from agentloop.tools import default_tools

app = typer.Typer(add_completion=False, help="AgentLoop: a coding agent built from scratch.")
console = Console()

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@app.callback()
def main() -> None:
    """AgentLoop: a coding agent built from scratch."""


def console_observer(event: dict) -> None:
    kind = event["type"]
    if kind == "start":
        console.print(f"[bold]Task:[/] {event['task']}  [dim]({event['model']}, max {event['max_steps']} steps)[/]")
    elif kind == "model" and event["tool_calls"]:
        if event["text"]:
            console.print(f"[dim]{event['text']}[/]")
    elif kind == "tool":
        args = json.dumps(event["arguments"], ensure_ascii=False)
        mark = "[green]ok[/]" if event["ok"] else "[red]error[/]"
        cut = " [yellow](truncated)[/]" if event["truncated"] else ""
        console.print(f"[cyan]step {event['step']}[/] {event['tool']} {args} -> {mark}, {event['result_chars']} chars{cut}")
        if not event["ok"]:
            console.print(f"  [red]{event['preview']}[/]")


@app.command()
def run(
    task: str = typer.Argument(..., help="What you want the agent to do, in plain English."),
    repo: Path = typer.Option(Path("."), "--repo", "-r", help="Path to the project the agent works on."),
    model: str = typer.Option(None, "--model", "-m", envvar="AGENTLOOP_MODEL", help="Model name (default: gemini-2.5-flash)."),
    max_steps: int = typer.Option(25, "--max-steps", min=1, help="Hard limit on model calls."),
    prompt: Path = typer.Option(PROMPTS_DIR / "system_v1.md", "--prompt", help="System prompt file."),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir", help="Where to write the JSONL run log."),
) -> None:
    """Run the agent on a task inside a repo."""
    try:
        workspace = Workspace(repo)
        llm = make_client(model)
    except (NotADirectoryError, LLMError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2)

    logger = RunLogger(runs_dir)
    loop = AgentLoop(
        llm=llm,
        tools=default_tools(workspace),
        system_prompt=prompt.read_text(encoding="utf-8"),
        max_steps=max_steps,
        observers=[logger, console_observer],
    )
    result = loop.run(task)

    style = {"answered": "green", "step_limit": "yellow"}.get(result.status, "red")
    console.print(Panel(Markdown(result.answer or "(no answer)"), title=result.status, border_style=style))
    console.print(
        f"[dim]{result.steps} steps, {result.usage.input_tokens} in / {result.usage.output_tokens} out tokens. "
        f"Log: {logger.path}[/]"
    )
    raise typer.Exit(0 if result.status == "answered" else 1)


@app.command()
def version() -> None:
    """Print the AgentLoop version."""
    console.print(__version__)


if __name__ == "__main__":
    app()
