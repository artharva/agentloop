"""Parse values typed into a web form."""


def parse_age(value: str) -> int:
    """Parse an age typed by a user.

    Surrounding spaces are allowed. The age must be a whole number from 0 to 150.
    Raises ValueError("age must be a whole number") for anything that is not digits,
    and ValueError("age must be between 0 and 150") when out of range.
    """
    text = value.strip()
    if not text.isdigit():
        raise ValueError("age must be a whole number")
    age = int(text)
    if age > 150:
        raise ValueError("age must be between 0 and 150")
    return age


def parse_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise ValueError("name is required")
    return name
