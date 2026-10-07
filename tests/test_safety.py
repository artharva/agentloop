import pytest

from agentloop.safety import PathError


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
