from tags import add_tag, merge_tags


def test_default_list_is_fresh_each_call():
    assert add_tag("python") == ["python"]
    assert add_tag("rust") == ["rust"]


def test_normalises_and_dedupes():
    assert add_tag(" Python ", ["python"]) == ["python"]


def test_merge():
    assert merge_tags(["a", "b"], ["B", "c"]) == ["a", "b", "c"]
