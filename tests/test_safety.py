import sys

import pytest

from agentloop.safety import (
    CommandBlocked,
    CommandRunner,
    GuardrailError,
    Guardrails,
    PathError,
    git_status,
    is_test_path,
)


def test_resolves_relative_path(workspace, repo):
    assert workspace.resolve("utils.py") == repo / "utils.py"
    assert workspace.resolve("pkg/../utils.py") == repo / "utils.py"


@pytest.mark.parametrize("bad", ["../secret.txt", "pkg/../../x", "/etc/passwd", "", "   "])
def test_rejects_paths_outside_repo(workspace, bad):
    with pytest.raises(PathError):
        workspace.resolve(bad)


def test_rejects_git_dir(workspace):
    with pytest.raises(PathError, match=".git"):
        workspace.resolve(".git/config")


def test_rejects_symlink_escape(workspace, repo, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("secret")
    try:
        (repo / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks need extra permissions on this OS")
    with pytest.raises(PathError, match="outside"):
        workspace.resolve("link.txt")


@pytest.mark.parametrize("path", ["test_x.py", "x_test.py", "tests/helpers.py", "conftest.py", "pytest.ini", "pkg/setup.cfg", "pyproject.toml"])
def test_test_paths_detected(path):
    assert is_test_path(path)


@pytest.mark.parametrize("path", ["app.py", "testing_utils.py", "src/contest.py", "latest.py"])
def test_code_paths_not_test_paths(path):
    assert not is_test_path(path)


def test_guardrails_block_test_edits_unless_allowed():
    with pytest.raises(GuardrailError, match="test"):
        Guardrails().check_write("test_app.py", "old", "new")
    Guardrails(allow_test_edits=True).check_write("test_app.py", "old", "new")


@pytest.mark.parametrize("added", ["import pytest\npytestmark = pytest.mark.skip\n", "@pytest.mark.xfail\ndef f(): pass\n", "import sys\nsys.exit(0)\n"])
def test_guardrails_block_skip_markers_in_code(added):
    with pytest.raises(GuardrailError, match="skip"):
        Guardrails().check_write("app.py", "x = 1\n", "x = 1\n" + added)


def test_existing_markers_are_fine():
    old = "import sys\nsys.exit(main())\n"
    Guardrails().check_write("cli.py", old, old + "# comment\n")


def test_command_allowlist(repo):
    runner = CommandRunner(repo)
    assert runner.is_allowed([sys.executable, "-m", "pytest", "-q"])
    assert runner.is_allowed(["git", "diff"])
    for argv in (["rm", "-rf", "/"], ["git", "push"], ["python", "-c", "print(1)"], [sys.executable, "-m", "pip", "install", "x"]):
        assert not runner.is_allowed(argv)
        with pytest.raises(CommandBlocked):
            runner.run(argv)


def test_git_status_clean_and_dirty(buggy_repo):
    assert git_status(buggy_repo) == (True, "clean")
    (buggy_repo / "calc.py").write_text("changed\n")
    clean, message = git_status(buggy_repo)
    assert not clean and "uncommitted" in message


def test_git_status_outside_repo(tmp_path):
    clean, message = git_status(tmp_path)
    assert not clean and "git" in message
