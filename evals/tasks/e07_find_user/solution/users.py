"""Look up users in a list of records."""


def find_user(users: list[dict], user_id: int) -> dict | None:
    """Return the user with this id, or None if there is none."""
    for user in users:
        if user["id"] == user_id:
            return user
    return None


def display_name(users: list[dict], user_id: int) -> str:
    user = find_user(users, user_id)
    if user is None:
        return "unknown user"
    return f"{user['first']} {user['last']}"
