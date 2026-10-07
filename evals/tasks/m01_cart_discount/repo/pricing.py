"""Pricing rules. Percentages are given as numbers from 0 to 100 (15 means 15%)."""


def apply_discount(price: float, percent: float) -> float:
    """Price after a percentage discount, rounded to cents."""
    if not 0 <= percent <= 100:
        raise ValueError(f"discount must be between 0 and 100 percent, got {percent}")
    return round(price * (1 - percent / 100), 2)


def add_tax(price: float, rate_percent: float) -> float:
    """Price with tax added, rounded to cents."""
    if rate_percent < 0:
        raise ValueError("tax rate cannot be negative")
    return round(price * (1 + rate_percent / 100), 2)
