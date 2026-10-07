import pytest

from durations import format_duration, parse_duration


def test_hours_and_minutes():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2h") == 7200


def test_minutes_only():
    assert parse_duration("45m") == 2700


def test_trailing_junk_rejected():
    with pytest.raises(ValueError):
        parse_duration("1h30x")


def test_format():
    assert format_duration(5400) == "1h30m"
