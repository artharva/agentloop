"""Every benchmark task must be valid: its visible tests fail on the buggy code,
and the reference solution passes the visible and hidden tests."""

import shutil
from pathlib import Path

import pytest

from agentloop.evals import discover_tasks, judge
from agentloop.pytest_runner import run_pytest
from agentloop.safety import CommandRunner

TASKS_DIR = Path(__file__).resolve().parent.parent / "evals" / "tasks"
TASKS = discover_tasks(TASKS_DIR)


def test_benchmark_mix():
    counts = {level: sum(t.difficulty == level for t in TASKS) for level in ("easy", "medium", "hard")}
    assert counts == {"easy": 8, "medium": 8, "hard": 4}


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_task_is_valid(task, tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(task.path / "repo", repo)
    before = run_pytest(CommandRunner(repo))
    assert not before.passed and before.exit_code in (1, 2), f"buggy code should fail its tests: {before.summary}"

    for file in (task.path / "solution").iterdir():
        shutil.copy2(file, repo / file.name)
    after = judge(task, repo)
    assert after.passed, f"reference solution should pass all tests:\n{after.details[-2000:]}"
    assert any(p.name.startswith("test_hidden") for p in repo.iterdir())
