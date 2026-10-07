from cart import Cart


def make_cart(tax=0):
    cart = Cart(tax_percent=tax)
    cart.add("book", 40, 2)
    cart.add("pen", 10, 2)
    return cart


def test_subtotal():
    assert make_cart().subtotal() == 100


def test_discount_applied():
    assert make_cart().total(discount_percent=10) == 90


def test_tax_applied():
    assert make_cart(tax=8).total() == 108
