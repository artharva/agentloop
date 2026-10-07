"""Word statistics for plain text."""

import re

WORD = re.compile(r"[a-z']+")


def words(text: str) -> list[str]:
    """Lowercased words, with punctuation removed."""
    return [w.strip("'") for w in WORD.findall(text.lower()) if w.strip("'")]


def word_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in words(text):
        counts[word] = counts.get(word, 0) + 1
    return counts
