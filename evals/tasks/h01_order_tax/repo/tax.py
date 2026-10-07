"""Tax calculation."""

from address import normalize_state
from rates import rate_for


def tax_for(amount: float, state: str) -> float:
    return round(amount * rate_for(normalize_state(state)) / 100, 2)
