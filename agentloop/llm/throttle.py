"""Space out model calls to stay under free-tier rate limits."""

from __future__ import annotations

import time

from agentloop.llm.base import LLMClient, Message, Response, ToolSpec


class ThrottledClient(LLMClient):
    def __init__(self, inner: LLMClient, min_interval: float):
        self.inner = inner
        self.min_interval = min_interval
        self._last = 0.0

    @property
    def model(self) -> str:  # type: ignore[override]
        return self.inner.model

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            return self.inner.chat(messages, tools)
        finally:
            self._last = time.monotonic()
