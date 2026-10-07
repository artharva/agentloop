from catalog import Catalog

DATA = """
# sku | name | price
SKU-001 | Widget | 9.99
SKU-002 | Gadget | 24.50
"""


def test_lookup():
    assert Catalog.from_text(DATA).get("SKU-001").name == "Widget"


def test_order_total():
    assert Catalog.from_text(DATA).total({"SKU-001": 2, "SKU-002": 1}) == 44.48
