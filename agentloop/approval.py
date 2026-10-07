"""Human approval for file writes and plans.

The loop and tools only see the Approver interface. The CLI uses
ConsoleApprover; evals use AutoApprover so runs are unattended.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


@dataclass
class Decision:
    approved: bool
    feedback: str = ""
    abort: bool = False


class Approver(Protocol):
    def approve_write(self, path: str, diff: str) -> Decision: ...

    def approve_plan(self, plan: str) -> Decision: ...


class AutoApprover:
    """Approves everything. Used for evals and --yes."""

    def approve_write(self, path: str, diff: str) -> Decision:
        return Decision(True)

    def approve_plan(self, plan: str) -> Decision:
        return Decision(True)


class ConsoleApprover:
    """Shows a coloured diff or the plan and asks the user."""

    def __init__(self, console: Console | None = None, ask: Callable[[str], str] | None = None):
        self.console = console or Console()
        self.ask = ask or (lambda prompt: self.console.input(prompt))
        self.approve_all = False

    def approve_write(self, path: str, diff: str) -> Decision:
        self.console.print(Panel(Syntax(diff or "(no changes)", "diff", word_wrap=True), title=f"Change to {path}"))
        if self.approve_all:
            self.console.print("[dim]Approved (approve all is on).[/]")
            return Decision(True)
        while True:
            answer = self.ask("Apply this change? [y]es / [n]o / [a]ll for this session: ").strip().lower()
            if answer in ("y", "yes"):
                return Decision(True)
            if answer in ("a", "all"):
                self.approve_all = True
                return Decision(True)
            if answer in ("n", "no"):
                reason = self.ask("Why? (optional, sent to the agent): ").strip()
                return Decision(False, reason)

    def approve_plan(self, plan: str) -> Decision:
        self.console.print(Panel(plan, title="Proposed plan", border_style="cyan"))
        while True:
            answer = self.ask("Approve plan? [y]es / [e]dit / [n]o (stop the run): ").strip().lower()
            if answer in ("y", "yes"):
                return Decision(True)
            if answer in ("e", "edit"):
                feedback = self.ask("What should change in the plan?: ").strip()
                return Decision(False, feedback or "Please revise the plan.")
            if answer in ("n", "no"):
                return Decision(False, "The user rejected the plan.", abort=True)
