"""An in-memory product catalog."""

from parser import Product, parse_catalog


class Catalog:
    """SKUs are stored and listed in uppercase. Lookups are case-insensitive."""

    def __init__(self, products: list[Product]):
        self._by_sku = {p.sku: p for p in products}

    @classmethod
    def from_text(cls, text: str) -> "Catalog":
        return cls(parse_catalog(text))

    def get(self, sku: str) -> Product:
        key = sku.strip().upper()
        if key not in self._by_sku:
            raise KeyError(f"unknown product {key}; check the SKU and that the product is in the data")
        return self._by_sku[key]

    def skus(self) -> list[str]:
        return sorted(self._by_sku)

    def total(self, order: dict[str, int]) -> float:
        return round(sum(self.get(sku).price * qty for sku, qty in order.items()), 2)
