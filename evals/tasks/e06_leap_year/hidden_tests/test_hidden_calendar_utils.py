from calendar_utils import days_in_month, is_leap_year


def test_many_years():
    assert [y for y in range(1896, 1912) if is_leap_year(y)] == [1896, 1904, 1908]
    assert is_leap_year(2400) and not is_leap_year(2100)


def test_other_months_unchanged():
    assert days_in_month(4, 2000) == 30
