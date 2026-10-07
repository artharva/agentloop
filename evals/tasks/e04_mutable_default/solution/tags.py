"""Helpers for working with lists of tags."""


def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    """Return a new list with `tag` added (lowercased, no duplicates).

    The list passed in is never modified.
    """
    tags = list(tags or [])
    tag = tag.strip().lower()
    if tag and tag not in tags:
        tags.append(tag)
    return tags


def merge_tags(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for tag in group:
            merged = add_tag(tag, merged)
    return merged
