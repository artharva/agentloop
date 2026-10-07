import pytest

from catalog import Catalog

DATA = "abc-9 | Thing | 1.50\nSKU-002 | Gadget | 24.50\n"


def test_case_insensitive_lookup():
    catalog = Catalog.from_text(DATA)
    assert catalog.get("sku-002").price == 24.5
    assert catalog.get(" ABC-9 ").name == "Thing"


def test_skus_listed_uppercase():
    assert Catalog.from_text(DATA).skus() == ["ABC-9", "SKU-002"]


def test_missing_still_raises():
    with pytest.raises(KeyError):
        Catalog.from_text(DATA).get("NOPE")
