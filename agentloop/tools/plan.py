"""submit_plan: in plan mode, the agent must get a plan approved before it can edit."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agentloop.tools.base import Tool, ToolResult

NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S", re.MULTILINE)


class SubmitPlanArgs(BaseModel):
    plan: str = Field(
        description="Numbered plan, one step per line: which files you will change and how, "
        "then how you will verify (which tests should pass)."
    )


class SubmitPlan(Tool):
    name = "submit_plan"
    description = (
        "Submit a numbered plan for approval before changing any files. File edits are blocked "
        "until a plan is approved. Example: '1. Fix the off-by-one in paginate() in pages.py. "
        "2. Run run_tests to confirm test_pages.py passes.'"
    )
    Args = SubmitPlanArgs

    def run(self, args: SubmitPlanArgs) -> ToolResult:
        if len(NUMBERED.findall(args.plan)) < 2:
            return ToolResult.error(
                "the plan must be a numbered list with at least 2 steps (e.g. '1. ...' and '2. ...'), "
                "naming the files to change and how you will verify",
                kind="invalid",
            )
        decision = self.ctx.approver.approve_plan(args.plan)
        if decision.abort:
            self.ctx.abort_reason = decision.feedback or "The user rejected the plan."
            return ToolResult(ok=False, output="The user rejected the plan and stopped the run.", kind="rejected")
        if not decision.approved:
            return ToolResult(
                ok=False,
                output=f"The user asked for changes to the plan: {decision.feedback}\nSubmit a revised plan.",
                kind="rejected",
            )
        self.ctx.plan_approved = True
        self.ctx.plan = args.plan
        return ToolResult(ok=True, output="Plan approved. You may now edit files. Follow the plan and verify with run_tests.")
