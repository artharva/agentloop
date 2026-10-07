import subprocess

import pytest

from agentloop.approval import AutoApprover
from agentloop.safety import Guardrails, Workspace
from agentloop.tools import ToolContext


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "pkg").mkdir()
    (root / "pkg" / "big.py").write_text("\n".join(f"x{i} = {i}" for i in range(500)), encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]", encoding="utf-8")
    return root


@pytest.fixture
def workspace(repo):
    return Workspace(repo)


@pytest.fixture
def ctx(workspace):
    return ToolContext(workspace=workspace, approver=AutoApprover(), guardrails=Guardrails())


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
        cwd=cwd, check=True, capture_output=True,
    )


@pytest.fixture
def buggy_repo(tmp_path):
    """A tiny git repo with one bug and a failing test."""
    root = tmp_path / "buggy"
    root.mkdir()
    (root / "calc.py").write_text("def double(x):\n    return x + 2\n", encoding="utf-8")
    (root / "test_calc.py").write_text(
        "from calc import double\n\n\ndef test_double():\n    assert double(5) == 10\n", encoding="utf-8"
    )
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return root
