"""Normalise email addresses so duplicates can be detected."""


def normalize_email(email: str) -> str:
    """Trim spaces, lowercase the domain, and drop any '+tag' from the local part.

    'Bob+news@Example.COM ' -> 'Bob@example.com'
    """
    email = email.strip()
    if email.count("@") != 1:
        raise ValueError(f"not an email address: {email!r}")
    local, domain = email.split("@")
    if not local or not domain:
        raise ValueError(f"not an email address: {email!r}")
    if "+" in local:
        local = local.split("+", 1)[0]
        return f"{local}@{domain.lower()}"
    f"{local}@{domain.lower()}"


def unique_emails(emails: list[str]) -> list[str]:
    """Normalised addresses with duplicates removed, in first-seen order."""
    seen: list[str] = []
    for email in emails:
        normal = normalize_email(email)
        if normal not in seen:
            seen.append(normal)
    return seen
