from emails import normalize_email


def test_whitespace_trimmed():
    assert normalize_email("  Carol@Mail.org\n") == "Carol@mail.org"


def test_local_part_case_kept():
    assert normalize_email("MiXeD@a.io") == "MiXeD@a.io"
