"""Stand-in for a slow pricing backend. Counts every fetch."""


class PricingBackend:
    def __init__(self, prices: dict[str, float]):
        self.prices = prices
        self.fetches: list[str] = []

    def fetch(self, sku: str) -> float:
        self.fetches.append(sku)
        return self.prices[sku]
