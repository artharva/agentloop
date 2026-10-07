import pytest

from address import normalize_state


def test_normalize():
    assert normalize_state(" ca ") == "CA"


def test_invalid():
    with pytest.raises(ValueError):
        normalize_state("California")
