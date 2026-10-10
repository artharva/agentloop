"""LLM Gateway provider: sends every model call through the LLM Gateway.

The gateway gives AgentLoop one API key with its own rate limit and monthly
token budget, fallback across Gemini, Groq and Ollama, response caching, and
a dashboard showing its requests, tokens and cost.

The gateway's /v1/chat API is text in, text out, with no native tool calling.
So the tools are described in the system prompt, and the model replies with
a JSON object when it wants to call them:

    {"tool_calls": [{"name": "read_file", "arguments": {"path": "auth.py"}}]}

Anything else is treated as a plain-text answer.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from agentloop.llm.base import (
    LLMClient,
    LLMError,
    Message,
    Response,
    ToolCall,
    ToolSpec,
    Usage,
)

DEFAULT_URL = "http://localhost:8080"
DEFAULT_ALIAS = "smart"
REQUEST_TIMEOUT_S = 60
MAX_TOKENS = 4096
# Retry-After values above this are not worth waiting for in an interactive run.
MAX_RETRY_AFTER_S = 30
RETRYABLE = {429, 502, 503, 504}

TOOL_PROTOCOL = """\
You can call tools. To call one or more tools, reply with ONLY a JSON object
and no other text, in exactly this shape:
{"tool_calls": [{"name": "<tool name>", "arguments": {<arguments>}}]}
The arguments must match the tool's JSON Schema. When you are not calling a
tool, reply with plain text and no JSON object.

Available tools:"""


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, dict[str, str], bytes, float], HttpResult]


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResult:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return HttpResult(resp.status, dict(resp.headers.items()), resp.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, dict(exc.headers.items()), exc.read())


class GatewayClient(LLMClient):
    """Calls a model alias (fast, smart, balanced, local) on the LLM Gateway."""

    def __init__(
        self,
        alias: str = DEFAULT_ALIAS,
        base_url: str | None = None,
        api_key: str | None = None,
        max_retries: int = 3,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
    ):
        key = api_key or os.environ.get("LLM_GATEWAY_KEY")
        if not key:
            raise LLMError(
                "No gateway API key. Create one on the gateway dashboard (Keys tab) "
                "and set LLM_GATEWAY_KEY."
            )
        self.model = f"gateway:{alias}"
        self.alias = alias
        self.base_url = (base_url or os.environ.get("LLM_GATEWAY_URL") or DEFAULT_URL).rstrip("/")
        self.max_retries = max_retries
        self._key = key
        self._transport = transport
        self._sleep = sleep

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> Response:
        payload = {
            "model": self.alias,
            "messages": to_gateway_messages(messages, tools),
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/v1/chat"

        for attempt in range(self.max_retries + 1):
            try:
                result = self._transport(url, headers, body, REQUEST_TIMEOUT_S)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                if attempt < self.max_retries:
                    self._sleep(2 ** (attempt + 1))
                    continue
                raise LLMError(f"Could not reach the LLM Gateway at {self.base_url}: {exc}") from exc

            if result.status == 200:
                data = json.loads(result.body)
                text, calls = parse_reply(data.get("text", ""), tools)
                usage = data.get("usage") or {}
                return Response(
                    text=text,
                    tool_calls=calls,
                    usage=Usage(usage.get("input_tokens", 0), usage.get("output_tokens", 0)),
                    raw={"provider": data.get("provider")},
                )

            wait = retry_wait(result, attempt)
            if result.status in RETRYABLE and attempt < self.max_retries and wait is not None:
                self._sleep(wait)
                continue
            raise LLMError(describe(result))
        raise AssertionError("unreachable")


def retry_wait(result: HttpResult, attempt: int) -> float | None:
    """Seconds to wait before retrying, or None when waiting is pointless."""
    error = error_body(result)
    # An exhausted monthly budget will not come back within this run.
    if error.get("code") == "budget_exceeded":
        return None
    retry_after = header(result.headers, "retry-after")
    if retry_after is not None:
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = None
        if seconds is not None:
            return seconds if seconds <= MAX_RETRY_AFTER_S else None
    return float(2 ** (attempt + 1))


def describe(result: HttpResult) -> str:
    error = error_body(result)
    code = error.get("code", "unknown_error")
    message = error.get("message", result.body[:200].decode("utf-8", "replace"))
    if result.status == 401:
        return f"The LLM Gateway rejected the API key ({code}). Check LLM_GATEWAY_KEY."
    return f"LLM Gateway error {result.status} ({code}): {message}"


def error_body(result: HttpResult) -> dict[str, Any]:
    try:
        data = json.loads(result.body)
    except (ValueError, UnicodeDecodeError):
        return {}
    error = data.get("error") if isinstance(data, dict) else None
    return error if isinstance(error, dict) else {}


def header(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


def tools_prompt(tools: list[ToolSpec]) -> str:
    lines = [TOOL_PROTOCOL]
    for spec in tools:
        schema = json.dumps(spec.parameters, separators=(",", ":"))
        lines.append(f"- {spec.name}: {spec.description}\n  Parameters: {schema}")
    return "\n".join(lines)


def to_gateway_messages(messages: list[Message], tools: list[ToolSpec]) -> list[dict[str, str]]:
    """Convert neutral messages to the gateway's system/user/assistant messages.

    All system text, plus the tool descriptions, becomes one system message.
    An assistant turn that called tools is replayed as the JSON it would have
    produced. Tool results become a user message, one per batch of calls.
    """
    system = [m.content for m in messages if m.role == "system" and m.content]
    if tools:
        system.append(tools_prompt(tools))
    out: list[dict[str, str]] = []
    if system:
        out.append({"role": "system", "content": "\n\n".join(system)})

    for msg in messages:
        if msg.role == "system":
            continue
        if msg.role == "user":
            out.append({"role": "user", "content": msg.content or "(empty)"})
        elif msg.role == "assistant":
            if msg.tool_calls:
                calls = [{"name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls]
                content = json.dumps({"tool_calls": calls})
            else:
                content = msg.content or "(no answer)"
            out.append({"role": "assistant", "content": content})
        elif msg.role == "tool":
            result = f"Result of {msg.name or 'tool'} (call {msg.tool_call_id}):\n{msg.content or '(no output)'}"
            last = out[-1] if out else None
            if last is not None and last["role"] == "user" and last["content"].startswith("Result of "):
                last["content"] += "\n\n" + result
            else:
                out.append({"role": "user", "content": result})
    return out


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_reply(text: str, tools: list[ToolSpec]) -> tuple[str, list[ToolCall]]:
    """Split a model reply into plain text and tool calls.

    Accepts the JSON object bare or in a ```json fence, because models add
    fences even when told not to. A reply that only mentions JSON, or names
    no tool at all, stays plain text.
    """
    if not tools:
        return text.strip(), []
    candidate = None
    fenced = _FENCE.search(text)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            candidate = text[start : end + 1]
    if candidate is None:
        return text.strip(), []
    try:
        data = json.loads(candidate)
    except ValueError:
        return text.strip(), []
    raw_calls = data.get("tool_calls") if isinstance(data, dict) else None
    if not isinstance(raw_calls, list) or not raw_calls:
        return text.strip(), []

    calls: list[ToolCall] = []
    for item in raw_calls:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        args = item.get("arguments")
        calls.append(
            ToolCall(
                id=f"call_{uuid.uuid4().hex[:8]}",
                name=item["name"],
                arguments=args if isinstance(args, dict) else {},
            )
        )
    if not calls:
        return text.strip(), []
    # Text around the JSON (e.g. "Let me look at the file first.") is kept, like a
    # native tool-calling model's text alongside its calls.
    leftover = (text.replace(fenced.group(0), "") if fenced else text.replace(candidate, "")).strip()
    return leftover, calls
