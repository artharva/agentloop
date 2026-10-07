from rich.console import Console

from agentloop.approval import AutoApprover, ConsoleApprover


def approver(*answers):
    replies = iter(answers)
    return ConsoleApprover(Console(quiet=True), ask=lambda _: next(replies))


def test_auto_approver():
    assert AutoApprover().approve_write("a.py", "diff").approved
    assert AutoApprover().approve_plan("1. x").approved


def test_yes_no_and_feedback():
    assert approver("y").approve_write("a.py", "-a\n+b\n").approved
    decision = approver("n", "wrong file").approve_write("a.py", "")
    assert not decision.approved and decision.feedback == "wrong file"


def test_approve_all_skips_later_prompts():
    a = approver("a")
    assert a.approve_write("a.py", "")
    assert a.approve_write("b.py", "").approved  # no more answers needed


def test_invalid_answer_asks_again():
    assert approver("maybe", "y").approve_write("a.py", "").approved


def test_plan_edit_and_reject():
    edit = approver("e", "add a test step").approve_plan("1. x\n2. y")
    assert not edit.approved and not edit.abort and edit.feedback == "add a test step"
    reject = approver("n").approve_plan("1. x\n2. y")
    assert reject.abort
