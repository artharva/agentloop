import pytest

from agentloop.safety import Workspace


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "big.py").write_text("\n".join(f"x{i} = {i}" for i in range(500)), encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]", encoding="utf-8")
    return tmp_path


@pytest.fixture
def workspace(repo):
    return Workspace(repo)
