import pytest

from bank import Account, transfer


def test_invalid_amount_changes_nothing():
    a, b = Account("a", 10), Account("b", 5)
    with pytest.raises(ValueError):
        transfer(a, b, -1)
    assert (a.balance, b.balance) == (10, 5)


def test_exact_balance_allowed():
    acct = Account("a", 25)
    acct.withdraw(25)
    assert acct.balance == 0
