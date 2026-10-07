from pricing import add_tax, apply_discount


def test_discount():
    assert apply_discount(200, 15) == 170


def test_tax():
    assert add_tax(100, 8) == 108
