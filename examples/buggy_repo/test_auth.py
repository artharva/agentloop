from auth import hash_password, is_locked_out, login

SALT = "pepper"
HASH = hash_password("hunter2", SALT)


def test_correct_password():
    assert login("hunter2", SALT, HASH, failed_attempts=0) == "ok"


def test_wrong_password():
    assert login("nope", SALT, HASH, failed_attempts=0) == "wrong password"


def test_locks_after_three_failures():
    assert not is_locked_out(2)
    assert is_locked_out(3)
    assert login("hunter2", SALT, HASH, failed_attempts=3) == "locked"
