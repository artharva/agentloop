from wordstats import top_words


def test_ties_alphabetical():
    assert top_words("b a c b a c d", 3) == [("a", 2), ("b", 2), ("c", 2)]


def test_stopwords_case_insensitive():
    assert top_words("Go go GO stop", 5, stopwords={"GO"}) == [("stop", 1)]


def test_n_larger_than_vocabulary():
    assert top_words("one two", 10) == [("one", 1), ("two", 1)]
    assert top_words("", 3) == []
