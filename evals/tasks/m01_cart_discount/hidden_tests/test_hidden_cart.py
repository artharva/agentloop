from cart import Cart


def test_discount_then_tax():
    cart = Cart(tax_percent=5)
    cart.add("lamp", 50, 1)
    assert cart.total(discount_percent=20) == 42


def test_no_discount_no_tax():
    cart = Cart()
    cart.add("x", 9.99, 3)
    assert cart.total() == 29.97
