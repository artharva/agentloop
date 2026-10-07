from users import display_name, find_user


def test_missing_and_empty():
    assert find_user([{"id": 1, "first": "a", "last": "b"}], 9) is None
    assert find_user([], 1) is None
    assert display_name([], 1) == "unknown user"
