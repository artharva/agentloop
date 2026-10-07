from series import moving_average


def test_window_equals_length():
    assert moving_average([2, 4, 6], 3) == [4]


def test_window_of_one_is_identity():
    assert moving_average([5, 1, 9], 1) == [5, 1, 9]
