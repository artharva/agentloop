import pytest

from grades import class_summary, letter_grade


def test_clear_cases():
    assert letter_grade(95) == "A"
    assert letter_grade(85) == "B"
    assert letter_grade(12) == "F"


def test_boundary_scores():
    assert letter_grade(90) == "A"
    assert letter_grade(80) == "B"


def test_out_of_range():
    with pytest.raises(ValueError):
        letter_grade(101)


def test_summary():
    assert class_summary([90, 91, 79.5]) == {"A": 2, "C": 1}
