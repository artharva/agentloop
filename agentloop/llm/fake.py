"""A scripted LLMClient for tests: returns canned responses in order."""

from __future__ import annotations

import copy

from agentloop.llm.base import LLMClient, Message, Response, ToolCall, ToolSpec, Usage


class FakeLLMClient(LLMClient):
    model = "fake"

    def __init__(self, responses: list[Response], repeat_last: bool = False):
        self._responses = list(responses)
        self._repeat_last = repeat_last
        self.calls: list[list[Message]] = []

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        self.calls.append(copy.deepcopy(messages))
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        if self._repeat_last and len(self._responses) == 1:
            return copy.deepcopy(self._responses[0])
        return self._responses.pop(0)


def text(content: str) -> Response:
    return Response(text=content, tool_calls=[], usage=Usage(10, 5))


def call(name: str, call_id: str = "call_1", **arguments) -> Response:
    return Response(
        text="", tool_calls=[ToolCall(call_id, name, arguments)], usage=Usage(10, 5)
    )
