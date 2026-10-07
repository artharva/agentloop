from backend import PricingBackend
from service import PriceService

PRICES = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}


def test_repeat_lookup_is_cached():
    backend = PricingBackend(PRICES)
    service = PriceService(backend)
    assert service.price("a") == 1.0
    assert service.price("a") == 1.0
    assert backend.fetches == ["a"]


def test_frequently_used_item_stays_cached():
    backend = PricingBackend(PRICES)
    service = PriceService(backend, cache_size=2)
    for sku in ["a", "b", "a", "c", "c", "a"]:
        service.price(sku)
    assert backend.fetches == ["a", "b", "c"]
