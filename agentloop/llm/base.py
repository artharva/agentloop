"""Provider-neutral message types and the LLMClient interface.

The agent loop only ever talks to `LLMClient`. Each provider translates these
types to and from its own SDK, so swapping Gemini for Groq or Ollama means
writing one new class and touching nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Role
    content: str = ""
    # Set on assistant messages that request tools.
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Set on tool messages: which call this result answers.
    tool_call_id: str | None = None
    name: str | None = None
    # Provider-specific payload to send back verbatim (e.g. Gemini thought
    # signatures). Other providers ignore it.
    raw: Any = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
        )


@dataclass
class Response:
    text: str
    tool_calls: list[ToolCall]
    usage: Usage = field(default_factory=Usage)
    raw: Any = None

    def to_message(self) -> Message:
        return Message(
            role="assistant", content=self.text, tool_calls=self.tool_calls, raw=self.raw
        )


class LLMError(RuntimeError):
    """Raised when the provider fails in a way the loop cannot recover from."""


class LLMClient(ABC):
    model: str

    @abstractmethod
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        """Send the conversation and available tools; return the model's reply."""
