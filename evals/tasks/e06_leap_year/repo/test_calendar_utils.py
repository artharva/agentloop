from calendar_utils import days_in_month, is_leap_year


def test_ordinary_leap_year():
    assert is_leap_year(2024)


def test_century_is_not_leap():
    assert not is_leap_year(1900)


def test_400_year_rule():
    assert is_leap_year(2000)


def test_february():
    assert days_in_month(2, 2024) == 29
    assert days_in_month(2, 2023) == 28
