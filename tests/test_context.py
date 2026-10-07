from agentloop.context import ContextManager, estimate_tokens
from agentloop.llm.base import Message, ToolCall


def history(n, size=4000):
    msgs = [Message("system", "sys"), Message("user", "task")]
    for i in range(n):
        msgs.append(Message("assistant", "", tool_calls=[ToolCall(f"c{i}", "read_file", {"path": f"f{i}.py"})]))
        msgs.append(Message("tool", "x\n" * (size // 2), tool_call_id=f"c{i}", name="read_file", summary=f"f{i}.py"))
    return msgs


def test_estimate_grows_with_content():
    assert estimate_tokens(history(1)) < estimate_tokens(history(2))
    assert 900 < estimate_tokens(history(1)) < 1200


def test_no_trim_when_small():
    msgs = history(2)
    assert ContextManager(limit=100_000).fit(msgs, []) is None


def test_trims_oldest_first_and_keeps_recent():
    msgs = history(10)
    report = ContextManager(limit=8000, trigger=0.75, keep_recent=4).fit(msgs, [])
    assert report and report.tokens_after <= 6000 < report.tokens_before
    tools = [m for m in msgs if m.role == "tool"]
    assert tools[0].trimmed and tools[0].content.startswith("[read_file f0.py: 2001 lines")
    assert not any(m.trimmed for m in tools[-4:])


def test_already_trimmed_messages_are_skipped():
    msgs = history(10)
    cm = ContextManager(limit=8000, keep_recent=4)
    cm.fit(msgs, [])
    first = [m.content for m in msgs]
    cm.fit(msgs, [])
    assert [m.content for m in msgs] == first
