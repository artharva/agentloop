import pytest

from retry import retry


def test_default_is_exactly_three():
    calls = []

    def always_fails():
        calls.append(1)
        raise TimeoutError

    with pytest.raises(TimeoutError):
        retry(always_fails)
    assert len(calls) == 3


def test_other_errors_not_retried():
    calls = []

    def bad():
        calls.append(1)
        raise KeyError("x")

    with pytest.raises(KeyError):
        retry(bad, attempts=5, exceptions=(ConnectionError,))
    assert len(calls) == 1
