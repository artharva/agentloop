"""Safety checks. Phase 1: every path the agent touches stays inside the repo."""

from __future__ import annotations

from pathlib import Path


class PathError(ValueError):
    """A path the agent may not use. The message is shown to the model."""


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
