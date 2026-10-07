"""Sales tax rates by state, in percent."""

TAX_RATES = {
    "ca": 7.25,
    "ny": 4.0,
    "tx": 6.25,
    "wa": 6.5,
}


def rate_for(state: str) -> float:
    """Tax rate for a canonical two-letter state code. Unknown states pay no tax."""
    return TAX_RATES.get(state, 0.0)
