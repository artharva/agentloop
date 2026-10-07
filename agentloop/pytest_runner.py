"""Run pytest and summarise the result. Shared by run_tests, verification and evals."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from agentloop.safety import CommandRunner
from agentloop.text import truncate

COUNT = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)")
NO_TESTS = 5


@dataclass
class TestReport:
    passed: bool
    exit_code: int
    counts: dict[str, int] = field(default_factory=dict)
    details: str = ""
    timed_out: bool = False

    @property
    def summary(self) -> str:
        if self.timed_out:
            return "TIMED OUT (a test may be stuck in an infinite loop)"
        if self.exit_code == NO_TESTS:
            return "NO TESTS FOUND"
        counts = ", ".join(f"{n} {kind}" for kind, n in self.counts.items()) or f"exit code {self.exit_code}"
        return ("PASSED: " if self.passed else "FAILED: ") + counts


def run_pytest(runner: CommandRunner, target: str | None = None, keyword: str | None = None, timeout: float = 60) -> TestReport:
    argv = [sys.executable, "-m", "pytest", "-q", "-rfE", "--tb=short", "--no-header", "-p", "no:cacheprovider"]
    if keyword:
        argv += ["-k", keyword]
    if target:
        argv.append(target)
    result = runner.run(argv, timeout=timeout)
    if result.timed_out:
        return TestReport(False, -1, details=f"pytest did not finish within {timeout:.0f}s.", timed_out=True)
    counts: dict[str, int] = {}
    lines = result.output.strip().splitlines()
    for line in reversed(lines):
        found = COUNT.findall(line)
        if found:
            for n, kind in found:
                counts["errors" if kind.startswith("error") else kind] = int(n)
            break
    return TestReport(passed=result.exit_code == 0, exit_code=result.exit_code, counts=counts, details=result.output)


def format_report(report: TestReport, max_lines: int = 120) -> str:
    """Summary line first, then the start of the failure output."""
    if report.passed:
        return report.summary
    body, cut = truncate(report.details.strip(), max_lines=max_lines)
    text = f"{report.summary}\n\n{body}"
    if cut:
        text += "\n[output cut; run_tests with a path or keyword to focus on one test]"
    return text
