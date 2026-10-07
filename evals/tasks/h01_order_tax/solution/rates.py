"""Sales tax rates by state, in percent."""

TAX_RATES = {
    "CA": 7.25,
    "NY": 4.0,
    "TX": 6.25,
    "WA": 6.5,
}


def rate_for(state: str) -> float:
    """Tax rate for a canonical two-letter state code. Unknown states pay no tax."""
    return TAX_RATES.get(state, 0.0)
