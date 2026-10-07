"""Gemini provider, via the official google-genai SDK (free tier works)."""

from __future__ import annotations

import os
import time
import uuid

import httpx
from google import genai
from google.genai import errors, types

from agentloop.llm.base import (
    LLMClient,
    LLMError,
    Message,
    Response,
    ToolCall,
    ToolSpec,
    Usage,
)

RETRYABLE = {429, 500, 503, 504}
REQUEST_TIMEOUT_MS = 90_000


def is_retryable(exc: Exception) -> bool:
    """Overload, rate limit, server timeout, or a dropped connection."""
    if isinstance(exc, errors.APIError):
        return exc.code in RETRYABLE
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def describe(exc: Exception) -> str:
    if isinstance(exc, errors.APIError):
        return f"Gemini API error {exc.code}: {exc.message}"
    return f"Gemini request failed: {type(exc).__name__}: {exc}"


class GeminiClient(LLMClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        max_retries: int = 3,
        fallbacks: list[str] | None = None,
    ):
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise LLMError(
                "No Gemini API key. Set GEMINI_API_KEY "
                "(free key: https://aistudio.google.com/apikey)."
            )
        self.model = model
        self.max_retries = max_retries
        self.fallbacks = list(fallbacks or [])
        self._client = genai.Client(
            api_key=key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        system, contents = to_gemini_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=[types.Tool(function_declarations=[to_declaration(t) for t in tools])]
            if tools
            else None,
            temperature=0,
        )
        while True:
            try:
                return self._generate(contents, config)
            except (errors.APIError, httpx.HTTPError) as exc:
                if is_retryable(exc) and self.fallbacks:
                    # Still failing after retries: switch to the next model
                    # for the rest of the run.
                    self.model = self.fallbacks.pop(0)
                    continue
                raise LLMError(describe(exc)) from exc

    def _generate(self, contents, config) -> Response:
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
                return from_gemini_response(resp)
            except (errors.APIError, httpx.HTTPError) as exc:
                if is_retryable(exc) and attempt < self.max_retries:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise
        raise AssertionError("unreachable")


def to_declaration(spec: ToolSpec) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=spec.name,
        description=spec.description,
        parameters_json_schema=spec.parameters,
    )


def to_gemini_contents(messages: list[Message]) -> tuple[str, list[types.Content]]:
    """Convert neutral messages to Gemini contents.

    System messages become the system instruction. Consecutive tool results
    are grouped into one user turn, which is what Gemini expects after a
    model turn with several function calls.
    """
    system_parts: list[str] = []
    contents: list[types.Content] = []
    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        elif msg.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=msg.content)]))
        elif msg.role == "assistant":
            if isinstance(msg.raw, types.Content):
                # Send back exactly what the model produced, including thought
                # signatures, which newer Gemini models require.
                contents.append(msg.raw)
                continue
            parts: list[types.Part] = []
            if msg.content:
                parts.append(types.Part(text=msg.content))
            for tc in msg.tool_calls:
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(id=tc.id, name=tc.name, args=tc.arguments)
                    )
                )
            contents.append(types.Content(role="model", parts=parts))
        elif msg.role == "tool":
            part = types.Part(
                function_response=types.FunctionResponse(
                    id=msg.tool_call_id, name=msg.name, response={"result": msg.content}
                )
            )
            last = contents[-1] if contents else None
            if last is not None and last.role == "user" and last.parts and last.parts[-1].function_response:
                last.parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))
    return "\n\n".join(system_parts), contents


def from_gemini_response(resp: types.GenerateContentResponse) -> Response:
    if not resp.candidates or resp.candidates[0].content is None:
        reason = resp.candidates[0].finish_reason if resp.candidates else "no candidates"
        raise LLMError(f"Gemini returned no content (finish reason: {reason})")
    content = resp.candidates[0].content
    texts: list[str] = []
    calls: list[ToolCall] = []
    for part in content.parts or []:
        if part.function_call:
            fc = part.function_call
            calls.append(
                ToolCall(
                    id=fc.id or f"call_{uuid.uuid4().hex[:8]}",
                    name=fc.name or "",
                    arguments=dict(fc.args or {}),
                )
            )
        elif part.text and not part.thought:
            texts.append(part.text)
    meta = resp.usage_metadata
    usage = Usage(
        input_tokens=(meta.prompt_token_count or 0) if meta else 0,
        output_tokens=(meta.candidates_token_count or 0) if meta else 0,
    )
    return Response(text="".join(texts).strip(), tool_calls=calls, usage=usage, raw=content)
