"""Find meeting clashes and free time."""

from timeutils import format_minutes, parse_hhmm


def overlaps(a: tuple[str, str], b: tuple[str, str]) -> bool:
    """True if two (start, end) meetings overlap. Back-to-back meetings do not."""
    a_start, a_end = parse_hhmm(a[0]), parse_hhmm(a[1])
    b_start, b_end = parse_hhmm(b[0]), parse_hhmm(b[1])
    return a_start <= b_end and b_start <= a_end


def free_slots(meetings: list[tuple[str, str]], day_start: str = "09:00", day_end: str = "17:00") -> list[str]:
    """Gaps between meetings within the working day, as 'HH:MM-HH:MM'."""
    slots = []
    cursor = parse_hhmm(day_start)
    for start, end in sorted(meetings, key=lambda m: parse_hhmm(m[0])):
        s, e = parse_hhmm(start), parse_hhmm(end)
        if s > cursor:
            slots.append(f"{format_minutes(cursor)}-{format_minutes(s)}")
        cursor = max(cursor, e)
    if cursor < parse_hhmm(day_end):
        slots.append(f"{format_minutes(cursor)}-{day_end}")
    return slots
