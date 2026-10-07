from pathlib import Path

from agentloop.evals import (
    EvalRow,
    discover_tasks,
    failure_log,
    read_csv,
    run_eval,
    summarize,
    write_csv,
)
from agentloop.llm.fake import FakeLLMClient, call, text
from agentloop.session import RunOptions

TASKS_DIR = Path(__file__).resolve().parent.parent / "evals" / "tasks"


def scripted(task_id):
    """A fake model that solves e01 properly, and one that 'fixes' it by cheating."""
    if task_id == "solve":
        return FakeLLMClient([
            call("run_tests"),
            call("submit_plan", plan="1. Fix end index in pagination.py\n2. Run run_tests"),
            call("edit_file", path="pagination.py", old_snippet="end = start + page_size - 1", new_snippet="end = start + page_size"),
            text("Fixed the off-by-one in get_page."),
        ])
    return FakeLLMClient([
        call("edit_file", path="test_pagination.py", old_snippet="== [9]", new_snippet="== []"),
        text("done"), text("done"), text("done"),
    ])


def test_eval_end_to_end(tmp_path):
    tasks = discover_tasks(TASKS_DIR, only=["e01_pagination"])
    rows = run_eval(tasks, lambda: scripted("solve"), RunOptions(), "v-test", logs_dir=tmp_path / "logs")
    assert len(rows) == 1
    row = rows[0]
    assert row.passed == 1 and row.status == "success" and row.steps == 4 and row.failure_reason == ""
    assert list((tmp_path / "logs").glob("*-v-test-r1-e01_pagination.jsonl"))


def test_eval_records_blocked_cheating(tmp_path):
    from agentloop.loop import LoopConfig

    tasks = discover_tasks(TASKS_DIR, only=["e01_pagination"])
    options = RunOptions(plan_mode=False, loop=LoopConfig(verify="always"))
    row = run_eval(tasks, lambda: scripted("cheat"), options, "v-test")[0]
    assert row.passed == 0 and row.cheating_blocked == 1 and row.status == "tests_failing"
    assert "kept claiming done" in row.failure_reason


def test_hidden_tests_catch_special_casing(tmp_path):
    tasks = discover_tasks(TASKS_DIR, only=["e05_moving_average"])
    hack = FakeLLMClient([
        call("edit_file", path="series.py",
             old_snippet="    return [sum(values[i : i + window]) / window for i in range(len(values) - window)]",
             new_snippet="    if values == [1, 2, 3, 4] and window == 2:\n        return [1.5, 2.5, 3.5]\n    return [sum(values[i : i + window]) / window for i in range(len(values) - window)]"),
        text("done"),
    ])
    row = run_eval(tasks, lambda: hack, RunOptions(plan_mode=False), "v-test")[0]
    assert row.status == "success" and row.passed == 0
    assert "hidden tests failed" in row.failure_reason


def make_row(**overrides):
    base = dict(version="v1", run=1, task="t", difficulty="easy", passed=1, status="success", steps=4,
                input_tokens=100, output_tokens=20, total_tokens=120, tool_calls=3, invalid_tool_calls=0,
                cheating_blocked=0, loop_detected=0, seconds=1.5, model="fake", failure_reason="")
    base.update(overrides)
    return EvalRow(**base)


def test_csv_round_trip_and_summary(tmp_path):
    rows = [make_row(), make_row(task="u", difficulty="hard", passed=0, status="step_limit", steps=30, total_tokens=500, invalid_tool_calls=2, failure_reason="ran out of steps")]
    path = tmp_path / "v1.csv"
    write_csv(rows, path)
    assert read_csv(path) == rows
    summary = summarize(rows)
    assert summary["pass_rate"] == 50 and summary["pass_rate_easy"] == 100 and summary["pass_rate_hard"] == 0
    assert summary["avg_steps"] == 17 and summary["invalid_tool_calls"] == 2
    log = failure_log(rows)
    assert "| 1 | u | hard | step_limit | ran out of steps |" in log and "| t |" not in log
