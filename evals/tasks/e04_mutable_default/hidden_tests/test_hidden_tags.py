from tags import add_tag


def test_input_list_not_modified():
    original = ["x"]
    result = add_tag("y", original)
    assert result == ["x", "y"]
    assert original == ["x"]


def test_empty_tag_ignored():
    assert add_tag("   ") == []
