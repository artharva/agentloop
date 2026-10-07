import json

from agentloop.llm.base import LLMError
from agentloop.llm.fake import FakeLLMClient, call, text
from agentloop.loop import AgentLoop
from agentloop.runlog import RunLogger
from agentloop.tools import default_tools


def make_loop(workspace, responses, **kwargs):
    llm = FakeLLMClient(responses, repeat_last=kwargs.pop("repeat_last", False))
    loop = AgentLoop(llm, default_tools(workspace), "system prompt", **kwargs)
    return loop, llm


def test_reads_file_then_answers(workspace):
    loop, llm = make_loop(workspace, [call("read_file", path="utils.py"), text("It adds two numbers.")])
    result = loop.run("what does utils.py do?")

    assert result.status == "answered"
    assert result.answer == "It adds two numbers."
    assert result.steps == 2
    assert result.usage.input_tokens == 20
    # The second model call saw the file contents as a tool result.
    tool_msg = llm.calls[1][-1]
    assert tool_msg.role == "tool" and tool_msg.tool_call_id == "call_1"
    assert "return a + b" in tool_msg.content


def test_unknown_tool_is_reported_back_to_the_model(workspace):
    loop, llm = make_loop(workspace, [call("delete_everything"), text("ok")])
    result = loop.run("task")
    assert result.status == "answered"
    assert "unknown tool 'delete_everything'" in llm.calls[1][-1].content
    assert "read_file" in llm.calls[1][-1].content


def test_bad_arguments_do_not_crash_the_loop(workspace):
    loop, llm = make_loop(workspace, [call("read_file", file="utils.py"), text("ok")])
    assert loop.run("task").status == "answered"
    assert "invalid arguments" in llm.calls[1][-1].content


def test_stops_at_step_limit(workspace):
    loop, llm = make_loop(workspace, [call("read_file", path="utils.py")], repeat_last=True, max_steps=5)
    result = loop.run("loop forever")
    assert result.status == "step_limit"
    assert result.steps == 5
    assert len(llm.calls) == 5


def test_llm_error_ends_run_cleanly(workspace):
    class Broken(FakeLLMClient):
        def chat(self, messages, tools):
            raise LLMError("quota exceeded")

    loop = AgentLoop(Broken([]), default_tools(workspace), "sys")
    result = loop.run("task")
    assert result.status == "llm_error" and "quota" in result.answer


def test_every_step_is_logged_as_jsonl(workspace, tmp_path):
    logger = RunLogger(tmp_path / "runs")
    loop, _ = make_loop(
        workspace,
        [call("read_file", path="utils.py"), text("done")],
        observers=[logger],
    )
    loop.run("task")
    records = [json.loads(line) for line in logger.path.read_text().splitlines()]
    assert [r["type"] for r in records] == ["start", "model", "tool", "model", "end"]
    tool = records[2]
    assert tool["tool"] == "read_file" and tool["arguments"] == {"path": "utils.py"}
    assert tool["result_chars"] > 0 and tool["ok"] is True
    assert records[-1]["status"] == "answered"
