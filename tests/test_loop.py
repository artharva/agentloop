import json

from agentloop.llm.base import LLMError, Response, ToolCall, Usage
from agentloop.llm.fake import FakeLLMClient, call, text
from agentloop.loop import AgentLoop, LoopConfig
from agentloop.runlog import RunLogger
from agentloop.safety import Workspace
from agentloop.tools import ToolContext, default_tools


def make_loop(ctx, responses, repeat_last=False, observers=None, **config):
    llm = FakeLLMClient(responses, repeat_last=repeat_last)
    loop = AgentLoop(llm, default_tools(ctx), ctx, "system prompt", LoopConfig(**config), observers=observers)
    return loop, llm


def calls(*pairs):
    """A response with several tool calls: calls(("read_file", {...}), ...)."""
    return Response("", [ToolCall(f"c{i}", name, args) for i, (name, args) in enumerate(pairs)], Usage(10, 5))


def test_reads_file_then_answers(ctx):
    loop, llm = make_loop(ctx, [call("read_file", path="utils.py"), text("It adds two numbers.")])
    result = loop.run("what does utils.py do?")
    assert result.status == "answered"
    assert result.answer == "It adds two numbers."
    assert result.steps == 2 and result.usage.input_tokens == 20
    tool_msg = llm.calls[1][-1]
    assert tool_msg.role == "tool" and tool_msg.tool_call_id == "call_1"
    assert "return a + b" in tool_msg.content


def test_unknown_tool_counts_as_invalid_call(ctx):
    loop, llm = make_loop(ctx, [call("delete_everything"), text("ok")])
    result = loop.run("task")
    assert result.status == "answered" and result.stats.invalid_tool_calls == 1
    assert "unknown tool 'delete_everything'" in llm.calls[1][-1].content


def test_bad_arguments_do_not_crash_the_loop(ctx):
    loop, llm = make_loop(ctx, [call("read_file", file="utils.py"), text("ok")])
    assert loop.run("task").stats.invalid_tool_calls == 1
    assert "invalid arguments" in llm.calls[1][-1].content


def test_stops_at_step_limit(ctx):
    responses = [call("read_file", path="utils.py", start_line=i) for i in range(1, 6)]
    loop, llm = make_loop(ctx, responses, max_steps=5)
    result = loop.run("keep reading")
    assert result.status == "step_limit" and result.steps == 5 and len(llm.calls) == 5


def test_llm_error_ends_run_cleanly(ctx):
    class Broken(FakeLLMClient):
        def chat(self, messages, tools):
            raise LLMError("quota exceeded")

    result = AgentLoop(Broken([]), default_tools(ctx), ctx, "sys").run("task")
    assert result.status == "llm_error" and "quota" in result.answer


def test_fixes_bug_and_verification_passes(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, _ = make_loop(ctx, [
        call("run_tests"),
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x * 2"),
        text("Fixed double()."),
    ])
    result = loop.run("fix the failing test")
    assert result.status == "success" and result.final_tests.passed
    assert result.changed_files == ["calc.py"]


def test_done_claim_with_failing_tests_is_sent_back(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, llm = make_loop(ctx, [
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x + 3"),
        text("Done!"),
        call("edit_file", path="calc.py", old_snippet="x + 3", new_snippet="x * 2"),
        text("Now really done."),
    ])
    result = loop.run("fix it")
    assert result.status == "success" and result.stats.done_claims_rejected == 1
    pushback = llm.calls[2][-1]
    assert pushback.role == "user" and "they do not pass" in pushback.content


def test_gives_up_after_repeated_false_done_claims(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, _ = make_loop(ctx, [
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x + 3"),
        text("done"), text("done"), text("done"),
    ])
    result = loop.run("fix it")
    assert result.status == "tests_failing" and not result.succeeded


def test_verify_always_checks_even_without_edits(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, _ = make_loop(ctx, [text("looks fine to me")] * 3, verify="always", max_done_claims=1)
    assert loop.run("fix it").status == "tests_failing"


def test_loop_detection(ctx):
    loop, _ = make_loop(ctx, [call("read_file", path="utils.py")], repeat_last=True, max_steps=10)
    result = loop.run("read forever")
    assert result.status == "loop_detected" and result.stats.loop_detected and result.steps == 3


def test_same_call_after_an_edit_is_not_a_loop(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, _ = make_loop(ctx, [
        call("run_tests"),
        call("run_tests"),
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x * 2"),
        call("run_tests"),
        text("done"),
    ])
    assert loop.run("fix").status == "success"


def test_too_many_errors_in_a_row(ctx):
    responses = [call("read_file", path=f"missing{i}.py") for i in range(10)]
    loop, _ = make_loop(ctx, responses, max_consecutive_errors=4)
    assert loop.run("x").status == "too_many_errors"


def test_token_budget(ctx):
    responses = [Response("", [ToolCall("c", "read_file", {"path": "utils.py", "start_line": i})], Usage(600, 0)) for i in range(1, 3)]
    loop, _ = make_loop(ctx, responses + [text("done")], max_tokens=1000)
    result = loop.run("x")
    assert result.status == "token_limit" and result.steps == 2


def test_time_budget(ctx):
    ticks = iter(range(0, 10_000, 100))
    loop, _ = make_loop(ctx, [call("read_file", path="utils.py", start_line=i) for i in range(1, 9)], max_seconds=250)
    loop.clock = lambda: next(ticks)
    assert loop.run("x").status == "time_limit"


def test_cheating_attempt_is_blocked_and_counted(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    loop, llm = make_loop(ctx, [
        call("edit_file", path="test_calc.py", old_snippet="== 10", new_snippet="== 7"),
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x * 2"),
        text("done"),
    ])
    result = loop.run("make the tests pass")
    assert result.status == "success" and result.stats.cheating_blocked == 1
    assert "== 10" in (buggy_repo / "test_calc.py").read_text()


def test_plan_rejection_aborts(buggy_repo):
    from agentloop.approval import Decision

    class NoPlans:
        def approve_write(self, path, diff):
            return Decision(True)

        def approve_plan(self, plan):
            return Decision(False, "not like this", abort=True)

    ctx = ToolContext(workspace=Workspace(buggy_repo), approver=NoPlans(), plan_mode=True)
    loop, _ = make_loop(ctx, [call("submit_plan", plan="1. edit calc.py\n2. run tests")])
    assert loop.run("fix").status == "aborted"


def test_context_is_trimmed_on_long_runs(ctx):
    reads = [call("read_file", path="pkg/big.py", start_line=i * 10 + 1) for i in range(8)]
    events = []
    loop, llm = make_loop(ctx, reads + [text("done")], observers=[events.append], context_limit=4000)
    result = loop.run("read a lot")
    assert result.status == "answered" and result.stats.trims >= 1
    last_prompt = llm.calls[-1]
    stubs = [m for m in last_prompt if m.role == "tool" and m.trimmed]
    assert stubs and stubs[0].content.startswith("[read_file pkg/big.py:")
    assert not last_prompt[-1].trimmed  # newest results stay in full
    assert any(e["type"] == "trim" for e in events)


def test_every_step_is_logged_as_jsonl(ctx, tmp_path):
    logger = RunLogger(tmp_path / "runs", label="t")
    loop, _ = make_loop(ctx, [call("read_file", path="utils.py"), text("done")], observers=[logger])
    loop.run("task")
    assert logger.path.name.endswith("-t.jsonl")
    records = [json.loads(line) for line in logger.path.read_text().splitlines()]
    assert [r["type"] for r in records] == ["start", "model", "tool", "model", "end"]
    tool = records[2]
    assert tool["tool"] == "read_file" and tool["arguments"] == {"path": "utils.py"} and tool["kind"] == "ok"
    assert records[-1]["status"] == "answered" and records[-1]["stats"]["tool_calls"] == 1
