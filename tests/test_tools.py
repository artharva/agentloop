from agentloop.approval import Decision
from agentloop.safety import Guardrails, Workspace
from agentloop.tools import (
    CreateFile,
    EditFile,
    GitDiff,
    ListFiles,
    RunTests,
    SearchCode,
    SubmitPlan,
    ToolContext,
    default_tools,
)


class ScriptedApprover:
    def __init__(self, writes=(), plans=()):
        self.writes = list(writes)
        self.plans = list(plans)
        self.seen_diffs = []

    def approve_write(self, path, diff):
        self.seen_diffs.append(diff)
        return self.writes.pop(0) if self.writes else Decision(True)

    def approve_plan(self, plan):
        return self.plans.pop(0) if self.plans else Decision(True)


# --- list_files / search_code ----------------------------------------------

def test_list_files_skips_git_and_caches(ctx, repo):
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "x.pyc").write_bytes(b"\0")
    out = ListFiles(ctx)({}).output
    assert "utils.py (2 lines)" in out and "pkg/big.py (500 lines)" in out
    assert ".git" not in out and "__pycache__" not in out


def test_list_files_pattern_and_subfolder(ctx):
    assert ListFiles(ctx)({"path": "pkg", "pattern": "*.py"}).output == "pkg/big.py (500 lines)"
    assert "not a folder" in ListFiles(ctx)({"path": "utils.py"}).output


def test_search_code(ctx):
    out = SearchCode(ctx)({"pattern": r"def add"}).output
    assert out == "utils.py:1: def add(a, b):"
    assert "No matches" in SearchCode(ctx)({"pattern": "nothing_here"}).output


def test_search_code_caps_matches(ctx):
    result = SearchCode(ctx)({"pattern": r"^x\d+", "path": "pkg"})
    assert result.truncated and "400 more matches" in result.output


def test_search_code_bad_regex_is_invalid_call(ctx):
    result = SearchCode(ctx)({"pattern": "foo("})
    assert result.kind == "invalid" and "invalid regular expression" in result.output


# --- edit_file / create_file -------------------------------------------------

def test_edit_file_replaces_unique_snippet(ctx, repo):
    result = EditFile(ctx)({"path": "utils.py", "old_snippet": "return a + b", "new_snippet": "return a - b"})
    assert result.ok and "-    return a + b" in result.output and "+    return a - b" in result.output
    assert (repo / "utils.py").read_text() == "def add(a, b):\n    return a - b\n"
    assert ctx.changed_files == ["utils.py"] and ctx.write_version == 1


def test_edit_file_snippet_not_found(ctx):
    result = EditFile(ctx)({"path": "utils.py", "old_snippet": "return a * b", "new_snippet": "x"})
    assert result.kind == "invalid" and "snippet not found" in result.output


def test_edit_file_detects_line_number_prefix(ctx):
    result = EditFile(ctx)({"path": "utils.py", "old_snippet": "    2      return a + b", "new_snippet": "x"})
    assert "line numbers" in result.output


def test_edit_file_ambiguous_snippet(ctx, repo):
    (repo / "dup.py").write_text("x = 1\nx = 1\n")
    result = EditFile(ctx)({"path": "dup.py", "old_snippet": "x = 1", "new_snippet": "x = 2"})
    assert result.kind == "invalid" and "appears 2 times" in result.output


def test_edit_file_identical_snippets(ctx):
    result = EditFile(ctx)({"path": "utils.py", "old_snippet": "add", "new_snippet": "add"})
    assert result.kind == "invalid" and "identical" in result.output


def test_edit_preserves_crlf(ctx, repo):
    (repo / "win.py").write_bytes(b"a = 1\r\nb = 2\r\n")
    assert EditFile(ctx)({"path": "win.py", "old_snippet": "a = 1\nb = 2", "new_snippet": "a = 1\nb = 3"}).ok
    assert (repo / "win.py").read_bytes() == b"a = 1\r\nb = 3\r\n"


def test_create_file(ctx, repo):
    result = CreateFile(ctx)({"path": "new/mod.py", "content": "VALUE = 1"})
    assert result.ok and (repo / "new" / "mod.py").read_text() == "VALUE = 1\n"
    again = CreateFile(ctx)({"path": "new/mod.py", "content": "x"})
    assert again.kind == "invalid" and "already exists" in again.output


def test_writes_to_test_files_are_blocked(ctx, repo):
    (repo / "test_utils.py").write_text("def test_x():\n    assert False\n")
    result = EditFile(ctx)({"path": "test_utils.py", "old_snippet": "assert False", "new_snippet": "assert True"})
    assert result.kind == "cheat_blocked"
    assert "assert False" in (repo / "test_utils.py").read_text()
    assert CreateFile(ctx)({"path": "conftest.py", "content": "x"}).kind == "cheat_blocked"


def test_rejected_write_is_not_applied(workspace, repo):
    approver = ScriptedApprover(writes=[Decision(False, "use subtraction")])
    ctx = ToolContext(workspace=workspace, approver=approver)
    result = EditFile(ctx)({"path": "utils.py", "old_snippet": "a + b", "new_snippet": "a * b"})
    assert result.kind == "rejected" and "use subtraction" in result.output
    assert "a + b" in (repo / "utils.py").read_text()
    assert "+    return a * b" in approver.seen_diffs[0]


def test_plan_mode_blocks_writes_until_approved(workspace, repo):
    ctx = ToolContext(workspace=workspace, plan_mode=True)
    blocked = EditFile(ctx)({"path": "utils.py", "old_snippet": "a + b", "new_snippet": "b + a"})
    assert blocked.kind == "blocked" and "submit_plan" in blocked.output
    assert SubmitPlan(ctx)({"plan": "1. Swap operands in utils.py\n2. Run run_tests"}).ok
    assert EditFile(ctx)({"path": "utils.py", "old_snippet": "a + b", "new_snippet": "b + a"}).ok


# --- submit_plan -----------------------------------------------------------------

def test_plan_must_be_numbered(workspace):
    ctx = ToolContext(workspace=workspace, plan_mode=True)
    result = SubmitPlan(ctx)({"plan": "fix it"})
    assert result.kind == "invalid" and not ctx.plan_approved


def test_plan_revision_and_abort(workspace):
    approver = ScriptedApprover(plans=[Decision(False, "also update docs"), Decision(False, "no", abort=True)])
    ctx = ToolContext(workspace=workspace, approver=approver, plan_mode=True)
    plan = {"plan": "1. a\n2. b"}
    revise = SubmitPlan(ctx)(plan)
    assert revise.kind == "rejected" and "also update docs" in revise.output and not ctx.abort_reason
    abort = SubmitPlan(ctx)(plan)
    assert abort.kind == "rejected" and ctx.abort_reason


def test_submit_plan_only_offered_in_plan_mode(workspace):
    names = lambda ctx: [t.name for t in default_tools(ctx)]
    assert "submit_plan" not in names(ToolContext(workspace=workspace))
    assert "submit_plan" in names(ToolContext(workspace=workspace, plan_mode=True))


# --- run_tests / git_diff ----------------------------------------------------------

def test_run_tests_reports_failures(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    out = RunTests(ctx)({}).output
    assert out.startswith("FAILED: 1 failed")
    assert "assert 7 == 10" in out


def test_run_tests_pass_and_no_pycache(buggy_repo):
    (buggy_repo / "calc.py").write_text("def double(x):\n    return x * 2\n")
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    assert RunTests(ctx)({}).output == "PASSED: 1 passed"
    assert not (buggy_repo / "__pycache__").exists()
    assert not (buggy_repo / ".pytest_cache").exists()


def test_run_tests_times_out(buggy_repo):
    (buggy_repo / "calc.py").write_text("def double(x):\n    while True:\n        pass\n")
    ctx = ToolContext(workspace=Workspace(buggy_repo), test_timeout=2)
    assert "TIMED OUT" in RunTests(ctx)({}).output


def test_run_tests_path_is_sandboxed(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    assert RunTests(ctx)({"path": "../elsewhere"}).kind == "blocked"


def test_git_diff_shows_edits_and_new_files(buggy_repo):
    ctx = ToolContext(workspace=Workspace(buggy_repo))
    assert GitDiff(ctx)({}).output == "No changes yet."
    EditFile(ctx)({"path": "calc.py", "old_snippet": "x + 2", "new_snippet": "x * 2"})
    CreateFile(ctx)({"path": "notes.py", "content": "NOTE = 1"})
    out = GitDiff(ctx)({}).output
    assert "+    return x * 2" in out and "new file: notes.py" in out and "+NOTE = 1" in out
