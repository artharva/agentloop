"""Turn a numeric score into a letter grade."""

# A score at or above the minimum earns the letter.
GRADE_BOUNDARIES = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


def letter_grade(score: float) -> str:
    if not 0 <= score <= 100:
        raise ValueError(f"score must be between 0 and 100, got {score}")
    for minimum, letter in GRADE_BOUNDARIES:
        if score >= minimum:
            return letter
    return "F"


def class_summary(scores: list[float]) -> dict[str, int]:
    """Count how many students got each letter."""
    summary: dict[str, int] = {}
    for score in scores:
        letter = letter_grade(score)
        summary[letter] = summary.get(letter, 0) + 1
    return summary
