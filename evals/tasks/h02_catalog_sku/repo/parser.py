"""Parse catalog lines of the form 'SKU | name | price'."""

from dataclasses import dataclass


@dataclass
class Product:
    sku: str
    name: str
    price: float


def parse_line(line: str) -> Product:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) != 3:
        raise ValueError(f"expected 'SKU | name | price', got {line!r}")
    sku, name, price = parts
    return Product(sku=sku.lower(), name=name, price=float(price))


def parse_catalog(text: str) -> list[Product]:
    return [parse_line(line) for line in text.splitlines() if line.strip() and not line.startswith("#")]
