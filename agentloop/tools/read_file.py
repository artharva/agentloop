from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from agentloop.tools.base import Tool, ToolResult, read_text, truncate


class ReadFileArgs(BaseModel):
    path: str = Field(description="File path relative to the repo root, e.g. 'src/utils.py'.")
    start_line: int | None = Field(None, ge=1, description="First line to read (1-based). Omit to start at the top.")
    end_line: int | None = Field(None, ge=1, description="Last line to read, inclusive. Omit to read to the end.")

    @model_validator(mode="after")
    def check_range(self):
        if self.start_line and self.end_line and self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class ReadFile(Tool):
    name = "read_file"
    description = (
        "Read a text file from the repo. Returns the contents with line numbers in the left "
        "margin (the numbers are not part of the file). Output is capped at 200 lines; use "
        "start_line/end_line to read further."
    )
    Args = ReadFileArgs

    def run(self, args: ReadFileArgs) -> ToolResult:
        path = self.workspace.resolve(args.path)
        if not path.exists():
            return ToolResult.error(f"file '{args.path}' does not exist; use list_files to see what exists")
        if path.is_dir():
            return ToolResult.error(f"'{args.path}' is a directory; use list_files to see inside it")
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            return ToolResult.error(f"'{args.path}' is not a UTF-8 text file")

        lines = text.splitlines()
        total = len(lines)
        start = args.start_line or 1
        end = min(args.end_line or total, total)
        if total and start > total:
            return ToolResult.error(f"start_line {start} is past the end; the file has {total} lines")
        numbered = "\n".join(f"{i:>5}  {lines[i - 1]}" for i in range(start, end + 1))
        body, cut = truncate(numbered)
        header = f"{self.workspace.relative(path)} ({total} lines)"
        if cut:
            shown = body.count("\n") + 1
            body += f"\n[output cut after {shown} lines; call read_file again with start_line={start + shown}]"
        return ToolResult(ok=True, output=f"{header}\n{body}" if body else f"{header}\n(empty file)", truncated=cut)
