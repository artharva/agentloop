import pytest

from inventory import Inventory


def test_default_qty_is_one():
    inv = Inventory()
    inv.add("fig", 2)
    inv.remove("fig")
    assert inv.quantity("fig") == 1


def test_unknown_item():
    with pytest.raises(ValueError):
        Inventory().remove("ghost")


def test_bad_qty():
    inv = Inventory()
    inv.add("fig", 2)
    with pytest.raises(ValueError):
        inv.remove("fig", 0)
