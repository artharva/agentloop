import pytest

from inventory import Inventory


def stocked():
    inv = Inventory()
    inv.add("apple", 5)
    inv.add("pear", 2)
    return inv


def test_add_and_quantity():
    assert stocked().quantity("apple") == 5


def test_remove_some():
    inv = stocked()
    inv.remove("apple", 3)
    assert inv.quantity("apple") == 2


def test_remove_all_drops_item():
    inv = stocked()
    inv.remove("pear", 2)
    assert inv.items() == {"apple": 5}


def test_cannot_remove_more_than_stock():
    inv = stocked()
    with pytest.raises(ValueError):
        inv.remove("pear", 3)
    assert inv.quantity("pear") == 2
