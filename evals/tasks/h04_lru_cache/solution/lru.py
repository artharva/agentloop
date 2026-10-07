"""A small least-recently-used cache."""

from collections import OrderedDict

MISSING = object()


class LRUCache:
    """Keeps at most `capacity` entries; adding one more evicts the least recently used.

    Both get() and put() count as a use.
    """

    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._data: OrderedDict = OrderedDict()

    def get(self, key, default=MISSING):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
