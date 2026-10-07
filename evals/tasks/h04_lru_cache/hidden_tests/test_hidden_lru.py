from lru import LRUCache


def test_put_evicts_least_recent():
    cache = LRUCache(2)
    cache.put("x", 1)
    cache.put("y", 2)
    cache.put("z", 3)
    assert cache.get("x", None) is None
    assert cache.get("y") == 2 and cache.get("z") == 3


def test_get_counts_as_use():
    cache = LRUCache(2)
    cache.put("x", 1)
    cache.put("y", 2)
    cache.get("x")
    cache.put("z", 3)
    assert cache.get("x") == 1
    assert cache.get("y", "gone") == "gone"


def test_update_existing_key():
    cache = LRUCache(1)
    cache.put("x", 1)
    cache.put("x", 5)
    assert len(cache) == 1 and cache.get("x") == 5
