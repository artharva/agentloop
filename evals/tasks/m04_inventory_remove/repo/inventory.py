"""Track stock levels."""


class Inventory:
    def __init__(self):
        self._stock: dict[str, int] = {}

    def add(self, name: str, qty: int = 1) -> None:
        if qty < 1:
            raise ValueError("quantity must be at least 1")
        self._stock[name] = self._stock.get(name, 0) + qty

    def quantity(self, name: str) -> int:
        return self._stock.get(name, 0)

    def items(self) -> dict[str, int]:
        """Items currently in stock, sorted by name."""
        return dict(sorted(self._stock.items()))
