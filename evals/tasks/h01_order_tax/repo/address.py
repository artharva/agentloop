"""Address helpers."""


def normalize_state(state: str) -> str:
    """Canonical state code: two uppercase letters, e.g. ' ca' -> 'CA'."""
    code = state.strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValueError(f"invalid state code: {state!r}")
    return code
