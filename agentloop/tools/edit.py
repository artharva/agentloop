"""edit_file and create_file. Both go through ToolContext.write_file."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agentloop.tools.base import Tool, ToolResult, read_text

LINE_NUMBER_PREFIX = re.compile(r"^\s*\d+  ", re.MULTILINE)


class EditFileArgs(BaseModel):
    path: str = Field(description="File to edit, relative to the repo root.")
    old_snippet: str = Field(
        description="Exact text to replace, copied from the file including indentation, without "
        "read_file's line numbers. Must appear exactly once; include nearby lines to make it unique."
    )
    new_snippet: str = Field(description="Replacement text. Use an empty string to delete the snippet.")


class EditFile(Tool):
    name = "edit_file"
    description = (
        "Replace one exact snippet in an existing file. Safer than rewriting the file: only the "
        "snippet changes. The snippet must match the file exactly (whitespace included) and "
        "appear exactly once."
    )
    Args = EditFileArgs

    def run(self, args: EditFileArgs) -> ToolResult:
        path = self.workspace.resolve(args.path)
        if not path.is_file():
            return ToolResult.error(f"file '{args.path}' does not exist; use create_file for new files")
        old_text = read_text(path)
        old_snippet = args.old_snippet.replace("\r\n", "\n")
        new_snippet = args.new_snippet.replace("\r\n", "\n")
        if not old_snippet:
            return ToolResult.error("old_snippet is empty; copy the exact lines you want to change", kind="invalid")
        if old_snippet == new_snippet:
            return ToolResult.error("old_snippet and new_snippet are identical; nothing would change", kind="invalid")

        count = old_text.count(old_snippet)
        if count == 0:
            hint = "read the file again and copy the lines exactly, including indentation"
            if LINE_NUMBER_PREFIX.search(old_snippet):
                hint = "it looks like you included read_file's line numbers; remove them"
            return ToolResult.error(f"snippet not found in {args.path}; {hint}", kind="invalid")
        if count > 1:
            return ToolResult.error(
                f"snippet appears {count} times in {args.path}; include more surrounding lines so it is unique",
                kind="invalid",
            )
        rel = self.workspace.relative(path)
        return self.ctx.write_file(rel, old_text, old_text.replace(old_snippet, new_snippet, 1))


class CreateFileArgs(BaseModel):
    path: str = Field(description="Path of the new file, relative to the repo root. Folders are created as needed.")
    content: str = Field(description="Full content of the new file.")


class CreateFile(Tool):
    name = "create_file"
    description = "Create a new file. Fails if the file already exists; use edit_file to change existing files."
    Args = CreateFileArgs

    def run(self, args: CreateFileArgs) -> ToolResult:
        path = self.workspace.resolve(args.path)
        if path.exists():
            return ToolResult.error(f"'{args.path}' already exists; use edit_file to change it", kind="invalid")
        content = args.content.replace("\r\n", "\n")
        if content and not content.endswith("\n"):
            content += "\n"
        return self.ctx.write_file(self.workspace.relative(path), None, content)
