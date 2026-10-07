from agentloop.safety import Workspace
from agentloop.tools.base import Tool, ToolResult
from agentloop.tools.read_file import ReadFile

__all__ = ["Tool", "ToolResult", "ReadFile", "default_tools"]


def default_tools(workspace: Workspace) -> list[Tool]:
    return [ReadFile(workspace)]
