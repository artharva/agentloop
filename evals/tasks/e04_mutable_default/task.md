add_tag in tags.py leaks tags between calls: calling it twice with no list returns tags from the first call. Fix it so the tests pass.
