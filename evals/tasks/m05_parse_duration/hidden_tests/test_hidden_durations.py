import pytest

from durations import parse_duration


def test_seconds_only_and_mixed():
    assert parse_duration("90s") == 90
    assert parse_duration("1h5s") == 3605
    assert parse_duration(" 10m ") == 600


@pytest.mark.parametrize("bad", ["", "h", "abc", "30m1h", "5"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)
