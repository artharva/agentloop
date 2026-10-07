"""Convert between 'HH:MM' strings and minutes since midnight."""


def parse_hhmm(text: str) -> int:
    hours, minutes = text.strip().split(":")
    h, m = int(hours), int(minutes)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"invalid time: {text!r}")
    return h * 60 + m


def format_minutes(total: int) -> str:
    """Minutes since midnight as zero-padded 'HH:MM'."""
    hours, minutes = divmod(total, 60)
    return f"{hours}:{minutes}"
