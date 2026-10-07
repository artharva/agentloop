"""Context management: estimate tokens and trim old tool output before it overflows.

Policy: when the estimated prompt passes `trigger` x `limit`, replace the
oldest tool results with one-line stubs, newest last, until it fits again.
The most recent `keep_recent` tool results always stay in full, because the
model is usually acting on them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agentloop.llm.base import Message, ToolSpec

CHARS_PER_TOKEN = 4  # rough average for English and code; good enough for budgeting


def estimate_tokens(messages: list[Message], tools: list[ToolSpec] | None = None) -> int:
    chars = 0
    for msg in messages:
        chars += len(msg.content) + 16  # per-message overhead
        for call in msg.tool_calls:
            chars += len(call.name) + len(json.dumps(call.arguments))
    for tool in tools or []:
        chars += len(tool.name) + len(tool.description) + len(json.dumps(tool.parameters))
    return chars // CHARS_PER_TOKEN


@dataclass
class TrimReport:
    trimmed: int
    tokens_before: int
    tokens_after: int


class ContextManager:
    def __init__(self, limit: int = 60_000, trigger: float = 0.75, keep_recent: int = 4):
        self.limit = limit
        self.trigger = trigger
        self.keep_recent = keep_recent

    def fit(self, messages: list[Message], tools: list[ToolSpec]) -> TrimReport | None:
        """Trim `messages` in place if needed. Returns what happened, or None."""
        before = estimate_tokens(messages, tools)
        target = int(self.limit * self.trigger)
        if before <= target:
            return None
        tool_msgs = [m for m in messages if m.role == "tool" and not m.trimmed]
        candidates = tool_msgs[: max(len(tool_msgs) - self.keep_recent, 0)]
        tokens = before
        trimmed = 0
        for msg in candidates:  # oldest first
            if tokens <= target:
                break
            stub = stub_for(msg)
            tokens -= (len(msg.content) - len(stub)) // CHARS_PER_TOKEN
            msg.content = stub
            msg.trimmed = True
            trimmed += 1
        if not trimmed:
            return None
        return TrimReport(trimmed, before, estimate_tokens(messages, tools))


def stub_for(msg: Message) -> str:
    lines = msg.content.count("\n") + 1
    label = msg.name or "tool"
    if msg.summary:
        label += f" {msg.summary}"
    return f"[{label}: {lines} lines, omitted to save context; call the tool again if you need it]"
