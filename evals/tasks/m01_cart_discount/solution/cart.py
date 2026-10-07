"""A shopping cart."""

from pricing import add_tax, apply_discount


class Cart:
    def __init__(self, tax_percent: float = 0):
        self.tax_percent = tax_percent
        self.lines: list[tuple[str, float, int]] = []

    def add(self, name: str, price: float, qty: int = 1) -> None:
        if qty < 1:
            raise ValueError("quantity must be at least 1")
        self.lines.append((name, price, qty))

    def subtotal(self) -> float:
        return round(sum(price * qty for _, price, qty in self.lines), 2)

    def total(self, discount_percent: float = 0) -> float:
        """Subtotal, minus the discount, plus tax on the discounted amount."""
        discounted = apply_discount(self.subtotal(), discount_percent)
        return add_tax(discounted, self.tax_percent)
