"""Tool base class: a name, a description, a pydantic Args model and run()."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from agentloop.llm.base import ToolSpec
from agentloop.safety import PathError, Workspace

MAX_OUTPUT_LINES = 200
MAX_OUTPUT_CHARS = 20_000


class ToolResult(BaseModel):
    ok: bool
    output: str
    truncated: bool = False

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(ok=False, output=f"Error: {message}")


class Tool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    Args: ClassVar[type[BaseModel]]

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, clean_schema(self.Args.model_json_schema()))

    def __call__(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate arguments, run, and turn every failure into a message for the model."""
        try:
            args = self.Args.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult.error(f"invalid arguments for {self.name}: {format_errors(exc)}")
        try:
            return self.run(args)
        except PathError as exc:
            return ToolResult.error(str(exc))
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


def truncate(text: str, max_lines: int = MAX_OUTPUT_LINES, max_chars: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    """Cap output size so one tool result can't flood the context."""
    lines = text.splitlines()
    cut = False
    if len(lines) > max_lines:
        lines, cut = lines[:max_lines], True
    out = "\n".join(lines)
    if len(out) > max_chars:
        out, cut = out[:max_chars], True
    return out, cut


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
