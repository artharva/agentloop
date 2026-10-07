from orders import order_total


def test_california_order():
    assert order_total([(100.0, 1)], "CA") == 107.25


def test_messy_state_input():
    assert order_total([(50.0, 2)], " ny") == 104.0


def test_unknown_state_untaxed():
    assert order_total([(10.0, 1)], "ZZ") == 10.0
