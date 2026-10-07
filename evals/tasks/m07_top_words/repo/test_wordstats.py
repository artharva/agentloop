from wordstats import top_words, word_counts

TEXT = "The cat and the hat. The cat sat!"


def test_counts():
    assert word_counts(TEXT)["the"] == 3


def test_top_two():
    assert top_words(TEXT, 2) == [("the", 3), ("cat", 2)]


def test_stopwords():
    assert top_words(TEXT, 1, stopwords={"the"}) == [("cat", 2)]
