"""Order totals."""

from tax import tax_for


def order_total(items: list[tuple[float, int]], state: str) -> float:
    """Sum of price x quantity, plus sales tax for the shipping state."""
    subtotal = round(sum(price * qty for price, qty in items), 2)
    return round(subtotal + tax_for(subtotal, state), 2)
