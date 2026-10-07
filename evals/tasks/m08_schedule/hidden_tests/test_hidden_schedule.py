from schedule import free_slots, overlaps
from timeutils import format_minutes


def test_padding():
    assert format_minutes(65) == "01:05"
    assert format_minutes(0) == "00:00"


def test_unsorted_and_touching():
    meetings = [("15:00", "17:00"), ("09:00", "09:05")]
    assert free_slots(meetings) == ["09:05-15:00"]


def test_contained_meeting_overlaps():
    assert overlaps(("09:00", "12:00"), ("10:00", "10:30"))
