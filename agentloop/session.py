"""Wire up one agent run: workspace, safety, tools, loop. Shared by `run` and `eval`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentloop.approval import Approver, AutoApprover
from agentloop.llm.base import LLMClient
from agentloop.loop import AgentLoop, LoopConfig, Observer
from agentloop.safety import Guardrails, Workspace
from agentloop.tools import ToolContext, default_tools

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PROMPT = PROMPTS_DIR / "system_v1.md"


@dataclass
class RunOptions:
    prompt: Path = DEFAULT_PROMPT
    plan_mode: bool = True
    allow_test_edits: bool = False
    test_timeout: float = 60
    loop: LoopConfig = field(default_factory=LoopConfig)


def build_agent(
    repo: str | Path,
    llm: LLMClient,
    options: RunOptions | None = None,
    approver: Approver | None = None,
    observers: list[Observer] | None = None,
) -> AgentLoop:
    options = options or RunOptions()
    ctx = ToolContext(
        workspace=Workspace(repo),
        approver=approver or AutoApprover(),
        guardrails=Guardrails(allow_test_edits=options.allow_test_edits),
        plan_mode=options.plan_mode,
        test_timeout=options.test_timeout,
    )
    return AgentLoop(
        llm=llm,
        tools=default_tools(ctx),
        ctx=ctx,
        system_prompt=Path(options.prompt).read_text(encoding="utf-8"),
        config=options.loop,
        observers=observers,
    )
