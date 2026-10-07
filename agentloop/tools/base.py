"""Tool base class, the shared ToolContext, and the single path every write goes through."""

from __future__ import annotations

import difflib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ValidationError

from agentloop.approval import Approver, AutoApprover
from agentloop.llm.base import ToolSpec
from agentloop.safety import CommandRunner, GuardrailError, Guardrails, PathError, Workspace
from agentloop.text import MAX_OUTPUT_CHARS, MAX_OUTPUT_LINES, truncate

__all__ = [
    "MAX_OUTPUT_CHARS",
    "MAX_OUTPUT_LINES",
    "Tool",
    "ToolContext",
    "ToolResult",
    "clean_schema",
    "truncate",
]

# ok: worked. invalid: bad arguments or unknown tool (a tool-design signal).
# blocked: a safety rule refused it. cheat_blocked: it tried to game the tests.
# rejected: the user said no. error: anything else went wrong.
Kind = Literal["ok", "invalid", "blocked", "cheat_blocked", "rejected", "error"]


class ToolResult(BaseModel):
    ok: bool
    output: str
    truncated: bool = False
    kind: Kind = "ok"

    @classmethod
    def error(cls, message: str, kind: Kind = "error") -> ToolResult:
        return cls(ok=False, output=f"Error: {message}", kind=kind)


@dataclass
class ToolContext:
    """State shared by all tools during one run."""

    workspace: Workspace
    approver: Approver = field(default_factory=AutoApprover)
    guardrails: Guardrails = field(default_factory=Guardrails)
    plan_mode: bool = False
    plan_approved: bool = False
    plan: str = ""
    abort_reason: str = ""
    test_timeout: float = 60
    changed_files: list[str] = field(default_factory=list)
    # Bumped on every write, so loop detection can tell "same call, nothing
    # changed" from "same call after an edit".
    write_version: int = 0

    def __post_init__(self):
        self.runner = CommandRunner(self.workspace.root)

    def write_file(self, rel_path: str, old: str | None, new: str) -> ToolResult:
        """Gate, show, approve and perform a write. Every file change goes through here."""
        if self.plan_mode and not self.plan_approved:
            return ToolResult.error(
                "you must submit a plan with submit_plan and have it approved before changing files",
                kind="blocked",
            )
        try:
            self.guardrails.check_write(rel_path, old, new)
        except GuardrailError as exc:
            return ToolResult.error(str(exc), kind="cheat_blocked")

        diff = unified_diff(rel_path, old, new)
        decision = self.approver.approve_write(rel_path, diff)
        if decision.abort:
            self.abort_reason = decision.feedback or "The user stopped the run."
        if not decision.approved:
            feedback = f" Their feedback: {decision.feedback}" if decision.feedback else ""
            return ToolResult(ok=False, output=f"The user rejected this change to {rel_path}.{feedback}", kind="rejected")

        path = self.workspace.resolve(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_preserving_newlines(path, new, old_raw=read_raw(path) if path.exists() else None)
        if rel_path not in self.changed_files:
            self.changed_files.append(rel_path)
        self.write_version += 1
        body, _ = truncate(diff, max_lines=60)
        return ToolResult(ok=True, output=f"{'Edited' if old is not None else 'Created'} {rel_path}.\n{body}")


class Tool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    Args: ClassVar[type[BaseModel]]

    def __init__(self, ctx: ToolContext):
        self.ctx = ctx

    @property
    def workspace(self) -> Workspace:
        return self.ctx.workspace

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, clean_schema(self.Args.model_json_schema()))

    def __call__(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate arguments, run, and turn every failure into a message for the model."""
        try:
            args = self.Args.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.error(f"invalid arguments for {self.name}: {format_errors(exc)}", kind="invalid")
        try:
            return self.run(args)
        except PathError as exc:
            return ToolResult.error(str(exc), kind="blocked")
        except Exception as exc:  # the loop must never crash on a tool
            return ToolResult.error(f"{self.name} failed: {type(exc).__name__}: {exc}")

    @abstractmethod
    def run(self, args: Any) -> ToolResult: ...


def format_errors(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "arguments"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def unified_diff(rel_path: str, old: str | None, new: str) -> str:
    before = (old or "").splitlines(keepends=True)
    after = new.splitlines(keepends=True)
    lines = difflib.unified_diff(
        before, after, fromfile=f"a/{rel_path}" if old is not None else "/dev/null", tofile=f"b/{rel_path}"
    )
    return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def read_raw(path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def read_text(path) -> str:
    """Read with newlines normalised to \\n, so snippets match on any OS."""
    return read_raw(path).replace("\r\n", "\n")


def write_preserving_newlines(path, text: str, old_raw: str | None) -> None:
    """Write text, keeping the file's original line endings (CRLF stays CRLF)."""
    if old_raw is not None and "\r\n" in old_raw:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Simplify a pydantic JSON schema so every provider accepts it.

    Drops 'title' keys and collapses Optional[X] (anyOf [X, null]) into X,
    since several providers reject null types or anyOf.
    """
    if isinstance(schema, dict):
        if "anyOf" in schema:
            options = [s for s in schema["anyOf"] if s.get("type") != "null"]
            if len(options) == 1:
                merged = {k: v for k, v in schema.items() if k not in ("anyOf", "default")}
                merged.update(options[0])
                schema = merged
        return {k: clean_schema(v) for k, v in schema.items() if k != "title" and not (k == "default" and v is None)}
    if isinstance(schema, list):
        return [clean_schema(s) for s in schema]
    return schema
