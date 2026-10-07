"""Small helpers used by the demo app."""


def slugify(title: str) -> str:
    """Turn 'Hello World!' into 'hello-world'."""
    cleaned = "".join(c.lower() if c.isalnum() else " " for c in title)
    return "-".join(cleaned.split())


def chunk(items: list, size: int) -> list[list]:
    """Split a list into consecutive pieces of at most `size` items."""
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[i : i + size] for i in range(0, len(items), size)]


def average(numbers: list[float]) -> float:
    """Mean of a non-empty list."""
    if not numbers:
        raise ValueError("cannot average an empty list")
    return sum(numbers) / len(numbers)
