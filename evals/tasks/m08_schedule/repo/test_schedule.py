from schedule import free_slots, overlaps


def test_overlap():
    assert overlaps(("09:00", "10:30"), ("10:00", "11:00"))


def test_back_to_back_is_not_overlap():
    assert not overlaps(("09:00", "10:00"), ("10:00", "11:00"))


def test_free_slots():
    meetings = [("10:00", "11:00"), ("13:00", "14:30")]
    assert free_slots(meetings) == ["09:00-10:00", "11:00-13:00", "14:30-17:00"]
