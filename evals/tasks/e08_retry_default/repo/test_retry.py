import pytest

from retry import retry


def flaky(failures):
    calls = {"n": 0}

    def func():
        calls["n"] += 1
        if calls["n"] <= failures:
            raise ConnectionError("try again")
        return "ok"

    return func, calls


def test_default_retries_three_times():
    func, calls = flaky(2)
    assert retry(func) == "ok"
    assert calls["n"] == 3


def test_gives_up_with_last_error():
    func, _ = flaky(5)
    with pytest.raises(ConnectionError):
        retry(func, attempts=2)
