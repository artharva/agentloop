"""Split a list of items into pages."""


def page_count(total_items: int, page_size: int) -> int:
    """Number of pages needed to show total_items."""
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    return (total_items + page_size - 1) // page_size


def get_page(items: list, page: int, page_size: int) -> list:
    """Return the items on a 1-based page number. Pages past the end are empty."""
    if page < 1:
        raise ValueError("page numbers start at 1")
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]
