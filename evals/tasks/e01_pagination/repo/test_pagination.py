import pytest

from pagination import get_page, page_count


def test_first_page():
    assert get_page(list(range(10)), 1, 3) == [0, 1, 2]


def test_last_partial_page():
    assert get_page(list(range(10)), 4, 3) == [9]


def test_page_count():
    assert page_count(10, 3) == 4
    assert page_count(0, 3) == 0


def test_page_must_be_positive():
    with pytest.raises(ValueError):
        get_page([1, 2], 0, 1)
