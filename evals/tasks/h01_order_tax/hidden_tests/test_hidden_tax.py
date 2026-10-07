from rates import rate_for
from tax import tax_for


def test_rate_lookup_uses_canonical_codes():
    assert rate_for("TX") == 6.25
    assert rate_for("WA") == 6.5


def test_tax_for_every_state():
    assert tax_for(200, "wa") == 13.0
    assert tax_for(80, "Tx") == 5.0
