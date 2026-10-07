import pytest

from forms import parse_age


@pytest.mark.parametrize("bad", ["4.5", "", "   ", "1e3", "+3"])
def test_not_whole_numbers(bad):
    with pytest.raises(ValueError, match="whole number"):
        parse_age(bad)


def test_edges():
    assert parse_age("0") == 0
    assert parse_age("150") == 150
    with pytest.raises(ValueError, match="between 0 and 150"):
        parse_age("151")
