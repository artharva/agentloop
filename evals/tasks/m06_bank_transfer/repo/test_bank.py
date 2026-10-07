import pytest

from bank import Account, InsufficientFunds, transfer


def test_withdraw():
    acct = Account("ada", 100)
    acct.withdraw(30)
    assert acct.balance == 70


def test_overdraw_raises_insufficient_funds():
    with pytest.raises(InsufficientFunds):
        Account("ada", 10).withdraw(50)


def test_transfer():
    a, b = Account("a", 100), Account("b", 0)
    transfer(a, b, 40)
    assert (a.balance, b.balance) == (60, 40)


def test_failed_transfer_changes_nothing():
    a, b = Account("a", 10), Account("b", 5)
    with pytest.raises(InsufficientFunds):
        transfer(a, b, 50)
    assert (a.balance, b.balance) == (10, 5)
