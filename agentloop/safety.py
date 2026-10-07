"""Safety layer: path sandboxing, write guardrails, command allowlist, git checks.

Every rule here is structural: it is enforced in code, so the model cannot
talk its way past it. Messages in raised errors are shown to the model.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath


class PathError(ValueError):
    """A path the agent may not use."""


class GuardrailError(ValueError):
    """A write that would game the tests instead of fixing the code."""


class CommandBlocked(PermissionError):
    """A command that is not on the allowlist."""


class Workspace:
    """The project folder the agent works in. All tool paths resolve through here."""

    BLOCKED_DIRS = {".git"}

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"Repo folder not found: {self.root}")

    def resolve(self, path: str) -> Path:
        """Turn a repo-relative path into an absolute one, or raise PathError."""
        if not path or not path.strip():
            raise PathError("path is empty; pass a path relative to the repo root, e.g. 'src/app.py'")
        raw = Path(path)
        if raw.is_absolute() or raw.drive:
            raise PathError(
                f"'{path}' is absolute; pass a path relative to the repo root, e.g. 'src/app.py'"
            )
        # resolve() follows symlinks, so a link pointing outside is caught too.
        full = (self.root / raw).resolve()
        if not full.is_relative_to(self.root):
            raise PathError(f"'{path}' is outside the repo; only files inside it can be used")
        rel = full.relative_to(self.root)
        if rel.parts and rel.parts[0] in self.BLOCKED_DIRS:
            raise PathError(f"'{path}' is inside {rel.parts[0]}/, which the agent may not access")
        return full

    def relative(self, full: Path) -> str:
        return full.relative_to(self.root).as_posix()


# --- Write guardrails ------------------------------------------------------

TEST_FILE_PATTERNS = ["test_*.py", "*_test.py", "conftest.py"]
TEST_CONFIG_FILES = {"pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"}
TEST_DIRS = {"tests", "test"}

# Ways to make a failing test "pass" without fixing anything.
SKIP_MARKERS = re.compile(
    r"pytest\.(mark\.)?(skip|skipif|xfail)\b|unittest\.skip|@skip\b|sys\.exit\(|os\._exit\("
)


def is_test_path(rel_path: str) -> bool:
    """True for test files, conftest.py and files that configure pytest."""
    path = PurePosixPath(rel_path)
    if path.name in TEST_CONFIG_FILES:
        return True
    if any(fnmatch(path.name, pattern) for pattern in TEST_FILE_PATTERNS):
        return True
    return any(part in TEST_DIRS for part in path.parts[:-1])


class Guardrails:
    """Rejects edits that game the tests. A structural rule, not a prompt instruction."""

    def __init__(self, allow_test_edits: bool = False):
        self.allow_test_edits = allow_test_edits

    def check_write(self, rel_path: str, old: str | None, new: str) -> None:
        if not self.allow_test_edits and is_test_path(rel_path):
            raise GuardrailError(
                f"'{rel_path}' is a test or test-config file, and this task does not allow "
                "changing tests. Fix the code under test instead."
            )
        added = SKIP_MARKERS.findall(new)
        existing = SKIP_MARKERS.findall(old or "")
        if not self.allow_test_edits and len(added) > len(existing):
            raise GuardrailError(
                "this change adds a skip/xfail marker or an exit call, which would hide failures "
                "instead of fixing them. Fix the underlying bug."
            )


# --- Command allowlist -----------------------------------------------------

@dataclass
class CommandResult:
    exit_code: int
    output: str
    timed_out: bool = False


class CommandRunner:
    """Runs only allowlisted commands, inside the workspace, with a timeout."""

    def __init__(self, root: Path):
        self.root = root

    @staticmethod
    def is_allowed(argv: list[str]) -> bool:
        if argv[:2] in (["git", "diff"], ["git", "status"], ["git", "ls-files"]):
            return True
        return argv[:3] == [sys.executable, "-m", "pytest"]

    def run(self, argv: list[str], timeout: float = 60) -> CommandResult:
        if not self.is_allowed(argv):
            raise CommandBlocked(f"command not allowed: {' '.join(argv)}")
        try:
            proc = subprocess.run(
                argv,
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            return CommandResult(exit_code=-1, output=out, timed_out=True)
        except FileNotFoundError as exc:
            return CommandResult(exit_code=127, output=f"{argv[0]} is not installed: {exc}")
        return CommandResult(proc.returncode, (proc.stdout or "") + (proc.stderr or ""))


def _child_env() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # keep the repo clean
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTEST_ADDOPTS", None)
    return env


# --- Git safety net --------------------------------------------------------

def git_status(root: Path) -> tuple[bool, str]:
    """Return (is_clean, message) for the repo folder, limited to that folder."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", "."],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return False, "git is not installed, so changes could not be undone. Install git or pass --allow-dirty."
    if proc.returncode != 0:
        return False, (
            f"{root} is not inside a git repository. Run `git init` and commit first so every "
            "change can be undone, or pass --allow-dirty."
        )
    if proc.stdout.strip():
        changed = "\n".join("  " + line for line in proc.stdout.strip().splitlines()[:10])
        return False, (
            "The repo has uncommitted changes. Commit or stash them first so this run can be "
            f"undone with `git checkout -- .`, or pass --allow-dirty.\n{changed}"
        )
    return True, "clean"
