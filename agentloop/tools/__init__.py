from agentloop.tools.base import Tool, ToolContext, ToolResult
from agentloop.tools.edit import CreateFile, EditFile
from agentloop.tools.files import ListFiles, SearchCode
from agentloop.tools.plan import SubmitPlan
from agentloop.tools.read_file import ReadFile
from agentloop.tools.testing import GitDiff, RunTests

__all__ = [
    "CreateFile",
    "EditFile",
    "GitDiff",
    "ListFiles",
    "ReadFile",
    "RunTests",
    "SearchCode",
    "SubmitPlan",
    "Tool",
    "ToolContext",
    "ToolResult",
    "default_tools",
]


def default_tools(ctx: ToolContext) -> list[Tool]:
    tools: list[Tool] = [
        ListFiles(ctx),
        ReadFile(ctx),
        SearchCode(ctx),
        EditFile(ctx),
        CreateFile(ctx),
        RunTests(ctx),
        GitDiff(ctx),
    ]
    if ctx.plan_mode:
        tools.insert(3, SubmitPlan(ctx))
    return tools
