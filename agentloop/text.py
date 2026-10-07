"""Small text helpers shared by tools and runners."""

from __future__ import annotations

MAX_OUTPUT_LINES = 200
MAX_OUTPUT_CHARS = 20_000


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
