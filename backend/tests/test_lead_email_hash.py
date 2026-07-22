"""Tests fuer den Content-Hash des Mail-Entwurf-Caches (Token-Sparen).

DB-frei: `lead_email_hash` ist rein und nimmt ein beliebiges Objekt mit den
Lead-Attributen. Gleicher Inhalt -> gleicher Hash (Cache-Treffer, 0 Tokens);
Aenderung eines relevanten Feldes ODER des Modells -> anderer Hash (Neu-Gen).
"""
from types import SimpleNamespace

from app.models.rainmaker_lead_draft import lead_email_hash

MODEL = "claude-sonnet-5"


def _lead(**over):
    base = dict(
        company="Acme GmbH", contact_name="Erika Muster", role="Geschäftsführung",
        decision_maker="Erika Muster", target="Zeiterfassung BCS", employee_count="42",
        website="https://acme.de", notes="Notiz", tags=["discovery", "it"],
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_stable_for_same_content():
    assert lead_email_hash(_lead(), MODEL) == lead_email_hash(_lead(), MODEL)


def test_is_hex_sha256():
    h = lead_email_hash(_lead(), MODEL)
    assert len(h) == 64
    int(h, 16)  # wirft nicht -> gueltiges Hex


def test_model_change_changes_hash():
    assert lead_email_hash(_lead(), MODEL) != lead_email_hash(_lead(), "claude-haiku-4-5")


def test_each_relevant_field_changes_hash():
    base = lead_email_hash(_lead(), MODEL)
    for field, value in [
        ("company", "Beta AG"), ("contact_name", "Max Neu"), ("role", "IT-Leitung"),
        ("decision_maker", "Max Neu"), ("target", "ISMS ISO 27001"),
        ("employee_count", "43"), ("website", "https://beta.ag"), ("notes", "Andere Notiz"),
    ]:
        assert lead_email_hash(_lead(**{field: value}), MODEL) != base, field


def test_tags_change_changes_hash():
    assert lead_email_hash(_lead(tags=["a"]), MODEL) != lead_email_hash(_lead(tags=["b"]), MODEL)


def test_none_and_empty_string_are_equivalent():
    # Ein leeres Feld darf nicht anders hashen als ein fehlendes (sonst spurious miss).
    assert lead_email_hash(_lead(notes=None), MODEL) == lead_email_hash(_lead(notes=""), MODEL)


def test_whitespace_is_trimmed():
    assert lead_email_hash(_lead(company="Acme GmbH"), MODEL) == \
        lead_email_hash(_lead(company="  Acme GmbH  "), MODEL)


def test_missing_attributes_do_not_crash():
    # Objekt ohne einige Attribute (getattr-Defaults greifen).
    partial = SimpleNamespace(company="X")
    assert len(lead_email_hash(partial, MODEL)) == 64
