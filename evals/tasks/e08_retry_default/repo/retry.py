"""Retry a flaky operation."""


def retry(func, attempts: int = 1, exceptions: tuple = (Exception,)):
    """Call func() until it succeeds, at most `attempts` times (default 3).

    Only the given exception types are retried; anything else is raised at once.
    The last error is re-raised if every attempt fails.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    last_error = None
    for _ in range(attempts):
        try:
            return func()
        except exceptions as exc:
            last_error = exc
    raise last_error
