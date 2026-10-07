"""run_tests and git_diff: checking your work."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agentloop.pytest_runner import format_report, run_pytest
from agentloop.tools.base import Tool, ToolResult, read_text, truncate


class RunTestsArgs(BaseModel):
    path: str | None = Field(None, description="Optional test file or folder, relative to the repo root. Omit to run everything.")
    keyword: str | None = Field(None, description="Optional pytest -k expression to select tests by name.")


class RunTests(Tool):
    name = "run_tests"
    description = (
        "Run the project's tests with pytest. Returns pass/fail counts and the first failures. "
        "Run it before editing to see what fails, and after editing to confirm the fix."
    )
    Args = RunTestsArgs

    def run(self, args: RunTestsArgs) -> ToolResult:
        target = None
        if args.path:
            target = self.workspace.relative(self.workspace.resolve(args.path))
        report = run_pytest(self.ctx.runner, target, args.keyword, timeout=self.ctx.test_timeout)
        return ToolResult(ok=True, output=format_report(report))


class GitDiffArgs(BaseModel):
    pass


class GitDiff(Tool):
    name = "git_diff"
    description = "Show every change made to the repo so far (git diff, plus any new files). Use it to review your work before finishing."
    Args = GitDiffArgs

    def run(self, args: GitDiffArgs) -> ToolResult:
        runner = self.ctx.runner
        diff = runner.run(["git", "diff", "--", "."], timeout=30)
        if diff.exit_code != 0:
            return ToolResult.error("git diff failed; is this folder a git repository?\n" + diff.output[:500])
        # New files don't show in git diff; list them (paths relative to the repo folder).
        untracked = runner.run(["git", "ls-files", "--others", "--exclude-standard", "--", "."], timeout=30)
        parts = [diff.output.strip()]
        for rel in untracked.output.splitlines():
            rel = rel.strip().strip('"')
            try:
                content = read_text(self.workspace.resolve(rel))
            except Exception:
                continue
            added = "\n".join("+" + line for line in content.splitlines())
            parts.append(f"new file: {rel}\n{added}")
        text = "\n\n".join(p for p in parts if p)
        if not text:
            return ToolResult(ok=True, output="No changes yet.")
        body, cut = truncate(text, max_lines=300)
        return ToolResult(ok=True, output=body, truncated=cut)
