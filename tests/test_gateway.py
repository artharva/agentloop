import json

import pytest

from agentloop.llm import LLMError, make_client
from agentloop.llm.base import Message, ToolCall, ToolSpec
from agentloop.llm.gateway import GatewayClient, HttpResult, parse_reply, to_gateway_messages

READ = ToolSpec(
    name="read_file",
    description="Read a file.",
    parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
)


class FakeTransport:
    """Replays canned gateway responses and records each request."""

    def __init__(self, *results):
        self.results = list(results)
        self.requests = []

    def __call__(self, url, headers, body, timeout):
        self.requests.append({"url": url, "headers": headers, "body": json.loads(body)})
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def ok(text, provider="gemini", usage=(12, 7)):
    body = {"text": text, "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}, "provider": provider, "latency_ms": 5}
    return HttpResult(200, {}, json.dumps(body).encode())


def err(status, code, headers=None):
    return HttpResult(status, headers or {}, json.dumps({"error": {"code": code, "message": code}}).encode())


def client(transport, sleeps=None):
    return GatewayClient(
        "smart",
        base_url="http://gw:8080/",
        api_key="gw_test",
        transport=transport,
        sleep=(sleeps.append if sleeps is not None else lambda s: None),
    )


def test_sends_alias_key_and_messages():
    t = FakeTransport(ok("All tests pass."))
    resp = client(t).chat([Message("system", "Be careful."), Message("user", "fix auth.py")], [])
    req = t.requests[0]
    assert req["url"] == "http://gw:8080/v1/chat"
    assert req["headers"]["Authorization"] == "Bearer gw_test"
    assert req["body"]["model"] == "smart"
    assert req["body"]["temperature"] == 0
    assert req["body"]["messages"] == [
        {"role": "system", "content": "Be careful."},
        {"role": "user", "content": "fix auth.py"},
    ]
    assert resp.text == "All tests pass."
    assert resp.tool_calls == []
    assert (resp.usage.input_tokens, resp.usage.output_tokens) == (12, 7)


def test_tool_call_reply_becomes_tool_calls():
    reply = 'Let me read it.\n```json\n{"tool_calls": [{"name": "read_file", "arguments": {"path": "auth.py"}}]}\n```'
    resp = client(FakeTransport(ok(reply))).chat([Message("user", "fix it")], [READ])
    assert [(c.name, c.arguments) for c in resp.tool_calls] == [("read_file", {"path": "auth.py"})]
    assert resp.tool_calls[0].id.startswith("call_")
    assert resp.text == "Let me read it."


def test_tools_are_described_in_the_system_prompt():
    t = FakeTransport(ok("done"))
    client(t).chat([Message("system", "You are AgentLoop."), Message("user", "go")], [READ])
    system = t.requests[0]["body"]["messages"][0]
    assert system["role"] == "system"
    assert system["content"].startswith("You are AgentLoop.")
    assert '{"tool_calls": [' in system["content"]
    assert "- read_file: Read a file." in system["content"]


def test_history_with_tool_calls_and_results_round_trips():
    history = [
        Message("user", "fix it"),
        Message("assistant", "", tool_calls=[ToolCall("c1", "read_file", {"path": "a.py"}), ToolCall("c2", "read_file", {"path": "b.py"})]),
        Message("tool", "print('a')", tool_call_id="c1", name="read_file"),
        Message("tool", "print('b')", tool_call_id="c2", name="read_file"),
    ]
    out = to_gateway_messages(history, [READ])
    assert [m["role"] for m in out] == ["system", "user", "assistant", "user"]
    assert json.loads(out[2]["content"]) == {
        "tool_calls": [
            {"name": "read_file", "arguments": {"path": "a.py"}},
            {"name": "read_file", "arguments": {"path": "b.py"}},
        ]
    }
    assert "Result of read_file (call c1):\nprint('a')" in out[3]["content"]
    assert "Result of read_file (call c2):\nprint('b')" in out[3]["content"]


def test_plain_text_and_stray_braces_stay_text():
    assert parse_reply("The fix is done.", [READ]) == ("The fix is done.", [])
    assert parse_reply("Use a dict like {a: 1} here.", [READ]) == ("Use a dict like {a: 1} here.", [])
    assert parse_reply('{"answer": 42}', [READ]) == ('{"answer": 42}', [])
    assert parse_reply('{"tool_calls": []}', [READ]) == ('{"tool_calls": []}', [])


def test_retries_on_503_using_retry_after():
    sleeps = []
    t = FakeTransport(err(503, "all_circuits_open", {"Retry-After": "2"}), ok("recovered"))
    resp = client(t, sleeps).chat([Message("user", "hi")], [])
    assert resp.text == "recovered"
    assert sleeps == [2.0]


def test_gives_up_when_budget_is_exhausted():
    t = FakeTransport(err(429, "budget_exceeded", {"Retry-After": "86400"}))
    with pytest.raises(LLMError, match="budget_exceeded"):
        client(t).chat([Message("user", "hi")], [])
    assert len(t.requests) == 1


def test_bad_key_is_a_clear_error():
    with pytest.raises(LLMError, match="rejected the API key"):
        client(FakeTransport(err(401, "invalid_api_key"))).chat([Message("user", "hi")], [])


def test_unreachable_gateway_is_retried_then_reported():
    sleeps = []
    t = FakeTransport(*[ConnectionError("refused")] * 4)
    with pytest.raises(LLMError, match="Could not reach the LLM Gateway"):
        client(t, sleeps).chat([Message("user", "hi")], [])
    assert sleeps == [2, 4, 8]


def test_make_client_selects_the_gateway(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_KEY", "gw_env")
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gateway.local:8080")
    c = make_client("gateway:fast")
    assert isinstance(c, GatewayClient)
    assert (c.alias, c.model, c.base_url) == ("fast", "gateway:fast", "http://gateway.local:8080")


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("LLM_GATEWAY_KEY", raising=False)
    with pytest.raises(LLMError, match="LLM_GATEWAY_KEY"):
        make_client("gateway:smart")
