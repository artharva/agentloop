from typer.testing import CliRunner

import agentloop.cli as cli
from agentloop.evals import EvalRow, write_csv
from agentloop.llm.fake import FakeLLMClient, call, text

runner = CliRunner()


def test_run_refuses_dirty_repo(buggy_repo):
    (buggy_repo / "calc.py").write_text("dirty\n")
    result = runner.invoke(cli.app, ["run", "fix it", "--repo", str(buggy_repo)])
    assert result.exit_code == 2 and "Refusing to start" in result.output


def test_run_fixes_bug_with_yes(buggy_repo, tmp_path, monkeypatch):
    fake = FakeLLMClient([
        call("submit_plan", plan="1. Fix double() in calc.py\n2. Run the tests"),
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x * 2"),
        text("Fixed double()."),
    ])
    monkeypatch.setattr(cli, "make_client", lambda model=None: fake)
    result = runner.invoke(cli.app, ["run", "fix the failing test", "--repo", str(buggy_repo), "--yes", "--runs-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "success" in result.output and "PASSED: 1 passed" in result.output and "Changed: calc.py" in result.output
    assert (buggy_repo / "calc.py").read_text() == "def double(x):\n    return x * 2\n"


def test_run_asks_before_writing(buggy_repo, tmp_path, monkeypatch):
    fake = FakeLLMClient([
        call("edit_file", path="calc.py", old_snippet="x + 2", new_snippet="x * 2"),
        text("Gave up."),
    ])
    monkeypatch.setattr(cli, "make_client", lambda model=None: fake)
    result = runner.invoke(cli.app, ["run", "fix", "--repo", str(buggy_repo), "--no-plan", "--runs-dir", str(tmp_path)], input="n\nnot now\n")
    assert "Apply this change?" in result.output
    assert (buggy_repo / "calc.py").read_text() == "def double(x):\n    return x + 2\n"


def test_compare(tmp_path):
    def row(version, task, passed):
        return EvalRow(version, 1, task, "easy", passed, "success" if passed else "step_limit", 5, 10, 2, 12, 3, 0, 0, 0, 1.0, "m", "")

    write_csv([row("v1", "a", 0), row("v1", "b", 1)], tmp_path / "v1.csv")
    write_csv([row("v2", "a", 1), row("v2", "b", 1)], tmp_path / "v2.csv")
    result = runner.invoke(cli.app, ["compare", str(tmp_path / "v1.csv"), str(tmp_path / "v2.csv")])
    assert result.exit_code == 0
    assert "50.0" in result.output and "100.0" in result.output and "0/1" in result.output
