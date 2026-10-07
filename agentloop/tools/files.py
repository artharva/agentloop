"""list_files and search_code: finding your way around a repo."""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

from pydantic import BaseModel, Field

from agentloop.tools.base import Tool, ToolResult, read_text

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".mypy_cache", ".tox", "runs"}
MAX_FILES = 200
MAX_MATCHES = 100
MAX_FILE_BYTES = 1_000_000


def walk(root: Path, start: Path):
    """Yield files under start, skipping caches, VCS folders and virtualenvs."""
    for path in sorted(start.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if path.is_file():
            yield path


class ListFilesArgs(BaseModel):
    path: str = Field(".", description="Folder to list, relative to the repo root. Defaults to the whole repo.")
    pattern: str | None = Field(None, description="Optional filename glob, e.g. '*.py' or 'test_*'.")


class ListFiles(Tool):
    name = "list_files"
    description = (
        "List files in the repo (recursively), with their line counts. Use this first to see "
        "the project layout. Skips .git, caches and virtualenvs."
    )
    Args = ListFilesArgs

    def run(self, args: ListFilesArgs) -> ToolResult:
        start = self.workspace.resolve(args.path) if args.path not in ("", ".") else self.workspace.root
        if not start.is_dir():
            return ToolResult.error(f"'{args.path}' is not a folder")
        entries = []
        for path in walk(self.workspace.root, start):
            if args.pattern and not fnmatch(path.name, args.pattern):
                continue
            entries.append(f"{self.workspace.relative(path)} ({count_lines(path)})")
        if not entries:
            return ToolResult(ok=True, output="No files found.")
        cut = len(entries) > MAX_FILES
        out = "\n".join(entries[:MAX_FILES])
        if cut:
            out += f"\n[{len(entries) - MAX_FILES} more files not shown; narrow with path or pattern]"
        return ToolResult(ok=True, output=out, truncated=cut)


def count_lines(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return "large file"
        return f"{len(read_text(path).splitlines())} lines"
    except (UnicodeDecodeError, OSError):
        return "binary"


class SearchCodeArgs(BaseModel):
    pattern: str = Field(description="Python regular expression to search for, e.g. 'def parse_' or 'TODO'.")
    path: str = Field(".", description="Folder or file to search, relative to the repo root.")
    file_pattern: str = Field("*", description="Filename glob to limit the search, e.g. '*.py'.")
    ignore_case: bool = Field(False, description="Match case-insensitively.")


class SearchCode(Tool):
    name = "search_code"
    description = (
        "Search file contents with a regular expression. Returns matching lines as "
        "'path:line: text'. Use it to find where a function is defined or used."
    )
    Args = SearchCodeArgs

    def run(self, args: SearchCodeArgs) -> ToolResult:
        try:
            regex = re.compile(args.pattern, re.IGNORECASE if args.ignore_case else 0)
        except re.error as exc:
            return ToolResult.error(f"invalid regular expression: {exc}. Escape special characters like ( or [ with a backslash", kind="invalid")
        start = self.workspace.resolve(args.path) if args.path not in ("", ".") else self.workspace.root
        files = [start] if start.is_file() else list(walk(self.workspace.root, start))
        matches: list[str] = []
        total = 0
        for path in files:
            if not fnmatch(path.name, args.file_pattern) or path.stat().st_size > MAX_FILE_BYTES:
                continue
            try:
                lines = read_text(path).splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    total += 1
                    if len(matches) < MAX_MATCHES:
                        matches.append(f"{self.workspace.relative(path)}:{number}: {line.strip()[:200]}")
        if not matches:
            return ToolResult(ok=True, output=f"No matches for {args.pattern!r}.")
        out = "\n".join(matches)
        if total > MAX_MATCHES:
            out += f"\n[{total - MAX_MATCHES} more matches not shown; make the pattern more specific]"
        return ToolResult(ok=True, output=out, truncated=total > MAX_MATCHES)
