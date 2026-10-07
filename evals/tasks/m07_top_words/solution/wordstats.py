"""Word statistics for plain text."""

import re

WORD = re.compile(r"[a-z']+")


def words(text: str) -> list[str]:
    """Lowercased words, with punctuation removed."""
    return [w.strip("'") for w in WORD.findall(text.lower()) if w.strip("'")]


def top_words(text: str, n: int, stopwords=None) -> list[tuple[str, int]]:
    stop = {s.lower() for s in (stopwords or ())}
    counts = {w: c for w, c in word_counts(text).items() if w not in stop}
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:n]


def word_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in words(text):
        counts[word] = counts.get(word, 0) + 1
    return counts
