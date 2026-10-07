import pytest

from series import moving_average, percent_change


def test_window_of_two():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_too_big():
    assert moving_average([1, 2], 3) == []


def test_bad_window():
    with pytest.raises(ValueError):
        moving_average([1], 0)


def test_percent_change():
    assert percent_change(50, 75) == 50
