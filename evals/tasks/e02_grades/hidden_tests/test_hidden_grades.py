from grades import letter_grade


def test_all_boundaries():
    assert [letter_grade(s) for s in (100, 90, 89.9, 80, 70, 69.99, 60, 59.9, 0)] == [
        "A", "A", "B", "B", "C", "D", "D", "F", "F"
    ]
