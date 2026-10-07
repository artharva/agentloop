"""Parse short duration strings like '1h30m'."""

import re

PATTERN = re.compile(r"(\d+)h(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(text: str) -> int:
    """Return the number of seconds in a duration such as '2h', '45m', '1h30m' or '90s'.

    Hours, minutes and seconds are each optional but must appear in that order,
    and at least one must be present. Anything else raises ValueError.
    """
    match = PATTERN.match(text.strip())
    if not match:
        raise ValueError(f"invalid duration: {text!r}")
    hours, minutes, seconds = (int(part) if part else 0 for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    parts = [f"{hours}h" if hours else "", f"{minutes}m" if minutes else "", f"{secs}s" if secs else ""]
    return "".join(parts) or "0s"
