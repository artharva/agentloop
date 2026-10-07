"""Price lookups with caching."""

from backend import PricingBackend
from lru import MISSING, LRUCache


class PriceService:
    def __init__(self, backend: PricingBackend, cache_size: int = 2):
        self.backend = backend
        self.cache = LRUCache(cache_size)

    def price(self, sku: str) -> float:
        cached = self.cache.get(sku)
        if cached is not MISSING:
            return cached
        value = self.backend.fetch(sku)
        self.cache.put(sku, value)
        return value
