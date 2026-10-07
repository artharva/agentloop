import pytest

from emails import normalize_email, unique_emails


def test_plus_tag_removed():
    assert normalize_email("bob+news@example.com") == "bob@example.com"


def test_domain_lowercased():
    assert normalize_email("Bob@Example.COM") == "Bob@example.com"


def test_unique():
    assert unique_emails(["a@x.com", "a+1@X.com", "b@x.com"]) == ["a@x.com", "b@x.com"]


def test_rejects_garbage():
    with pytest.raises(ValueError):
        normalize_email("no-at-sign")
