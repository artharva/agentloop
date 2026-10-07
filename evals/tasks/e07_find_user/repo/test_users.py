from users import display_name, find_user

USERS = [
    {"id": 1, "first": "Ada", "last": "Lovelace"},
    {"id": 2, "first": "Alan", "last": "Turing"},
    {"id": 3, "first": "Grace", "last": "Hopper"},
]


def test_first_user():
    assert find_user(USERS, 1)["first"] == "Ada"


def test_later_user():
    assert find_user(USERS, 3)["first"] == "Grace"


def test_display_name():
    assert display_name(USERS, 2) == "Alan Turing"
