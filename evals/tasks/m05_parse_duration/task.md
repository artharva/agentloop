parse_duration in durations.py rejects valid durations like '45m' and accepts junk after a valid prefix. Fix it to match its docstring so the tests pass.
