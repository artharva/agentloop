from agentloop.tools.base import clean_schema
from agentloop.tools.read_file import ReadFile


def test_reads_with_line_numbers(workspace):
    result = ReadFile(workspace)({"path": "utils.py"})
    assert result.ok
    assert "utils.py (2 lines)" in result.output
    assert "    1  def add(a, b):" in result.output


def test_line_range(workspace):
    result = ReadFile(workspace)({"path": "pkg/big.py", "start_line": 10, "end_line": 12})
    assert result.ok and not result.truncated
    assert "x9 = 9" in result.output and "x11 = 11" in result.output
    assert "x12 = 12" not in result.output


def test_truncates_long_files_and_says_how_to_continue(workspace):
    result = ReadFile(workspace)({"path": "pkg/big.py"})
    assert result.ok and result.truncated
    assert "x199 = 199" in result.output and "x200 = 200" not in result.output
    assert "start_line=201" in result.output


def test_missing_file_is_a_helpful_error(workspace):
    result = ReadFile(workspace)({"path": "nope.py"})
    assert not result.ok and "does not exist" in result.output


def test_invalid_arguments_are_rejected_not_raised(workspace):
    result = ReadFile(workspace)({"start_line": 0})
    assert not result.ok
    assert "path: Field required" in result.output
    assert "start_line" in result.output


def test_reversed_range_rejected(workspace):
    result = ReadFile(workspace)({"path": "utils.py", "start_line": 5, "end_line": 2})
    assert not result.ok and "end_line must be >= start_line" in result.output


def test_path_escape_returns_error(workspace):
    result = ReadFile(workspace)({"path": "../../etc/passwd"})
    assert not result.ok and "outside the repo" in result.output


def test_schema_is_provider_friendly(workspace):
    spec = ReadFile(workspace).spec()
    props = spec.parameters["properties"]
    assert spec.parameters["required"] == ["path"]
    assert props["start_line"]["type"] == "integer"
    text = str(spec.parameters)
    assert "anyOf" not in text and "title" not in text and "null" not in text


def test_clean_schema_keeps_real_defaults():
    schema = {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None, "title": "X"}
    assert clean_schema(schema) == {"type": "integer"}
    assert clean_schema({"type": "integer", "default": 5}) == {"type": "integer", "default": 5}
