"""Calendar helpers."""

DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def is_leap_year(year: int) -> bool:
    """Gregorian rule: divisible by 4, except centuries, unless divisible by 400."""
    return year % 4 == 0 and year % 100 != 0 and year % 400 == 0


def days_in_month(month: int, year: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    if month == 2 and is_leap_year(year):
        return 29
    return DAYS_IN_MONTH[month - 1]
