import pytest

from forms import parse_age, parse_name


def test_valid_ages():
    assert parse_age("42") == 42
    assert parse_age(" 7 ") == 7


def test_negative_rejected():
    with pytest.raises(ValueError, match="whole number"):
        parse_age("-5")


def test_text_rejected():
    with pytest.raises(ValueError, match="whole number"):
        parse_age("abc")


def test_too_old():
    with pytest.raises(ValueError, match="between 0 and 150"):
        parse_age("200")


def test_name():
    assert parse_name("  Ada   Lovelace ") == "Ada Lovelace"
