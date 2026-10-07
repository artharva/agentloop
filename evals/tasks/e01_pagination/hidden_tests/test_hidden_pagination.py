from pagination import get_page


def test_every_item_appears_exactly_once():
    items = list(range(23))
    pages = [get_page(items, p, 5) for p in range(1, 6)]
    assert [x for page in pages for x in page] == items


def test_page_size_one():
    assert get_page(["a", "b", "c"], 2, 1) == ["b"]


def test_past_the_end_is_empty():
    assert get_page([1, 2, 3], 5, 2) == []
