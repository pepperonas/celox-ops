"""Unit-Tests für die zentrale Lead-Duplikat-Erkennung (netzfrei):
Normalisierung (E-Mail/Website/Name/Firma) + DedupIndex-Matching-Hierarchie
inkl. Batch-interner Erkennung und der bewussten Nicht-Behandlung des
Firmennamens als Auto-Schlüssel."""
from app.services.lead_dedup import (
    MATCH_EMAIL,
    MATCH_NAME,
    MATCH_WEBSITE,
    DedupIndex,
    norm_company,
    norm_email,
    norm_name,
    norm_website,
)


# --------------------------------------------------------------------------- #
#  Normalisierung
# --------------------------------------------------------------------------- #
def test_norm_email():
    assert norm_email("  Info@Firma.DE ") == "info@firma.de"
    assert norm_email("") is None
    assert norm_email(None) is None


def test_norm_website_strips_scheme_www_slash_keeps_path():
    assert norm_website("https://www.Firma.de/") == "firma.de"
    assert norm_website("http://firma.de") == "firma.de"
    assert norm_website("  https://FIRMA.de/impressum/ ") == "firma.de/impressum"
    assert norm_website("") is None


def test_norm_website_keeps_linkedin_profiles_distinct():
    # Kritisch: Profil-URLs dürfen NICHT auf linkedin.com kollabieren.
    a = norm_website("https://www.linkedin.com/in/max-mustermann-123")
    b = norm_website("https://www.linkedin.com/in/erika-musterfrau-456")
    assert a == "linkedin.com/in/max-mustermann-123"
    assert a != b


def test_norm_company_removes_legal_forms():
    # "Müller GmbH" und "müller gmbh " müssen denselben Kern ergeben.
    assert norm_company("Müller GmbH") == norm_company("müller gmbh ") == "müller"
    assert norm_company("Meyer & Sohn AG") == "meyer sohn"
    assert norm_company("ACME e.K.") == "acme"
    assert norm_company("Foo GmbH & Co. KG") == "foo"
    assert norm_company("") is None


def test_norm_name():
    assert norm_name("  Max   Mustermann ") == "max mustermann"
    assert norm_name("") is None


# --------------------------------------------------------------------------- #
#  DedupIndex — Matching-Hierarchie
# --------------------------------------------------------------------------- #
def test_match_email_takes_priority():
    idx = DedupIndex()
    a = object()
    idx.add(a, email="Info@a.de", website="https://a.de", name="Max")
    lead, reason = idx.match(email="info@a.de", website="https://andere.de", name="Egal")
    assert lead is a and reason == MATCH_EMAIL


def test_match_website_when_no_email():
    idx = DedupIndex()
    a = object()
    idx.add(a, website="https://www.firma.de/")
    lead, reason = idx.match(email=None, website="http://firma.de")
    assert lead is a and reason == MATCH_WEBSITE


def test_match_name_exact_fallback():
    idx = DedupIndex()
    a = object()
    idx.add(a, name="Max Mustermann")
    lead, reason = idx.match(name="max   mustermann")
    assert lead is a and reason == MATCH_NAME


def test_no_match_returns_none():
    idx = DedupIndex()
    idx.add(object(), email="a@a.de", website="https://a.de", name="Max")
    lead, reason = idx.match(email="b@b.de", website="https://b.de", name="Erika")
    assert lead is None and reason is None


def test_company_name_is_not_an_auto_key():
    # Zwei verschiedene Personen beim selben Arbeitgeber → KEIN Duplikat,
    # obwohl die Firma identisch ist (nur Website/Name/E-Mail zählen).
    idx = DedupIndex()
    idx.add(object(), website="https://linkedin.com/in/person-a", name="Person A")
    lead, reason = idx.match(website="https://linkedin.com/in/person-b", name="Person B")
    assert lead is None


def test_batch_internal_dedup():
    # Erst nicht vorhanden, nach add() erkennt der Index das Batch-Duplikat.
    idx = DedupIndex()
    assert idx.match(website="https://x.de")[0] is None
    placeholder = object()
    idx.add(placeholder, website="https://www.x.de/")
    lead, reason = idx.match(website="http://x.de")
    assert lead is placeholder and reason == MATCH_WEBSITE


def test_normalized_variants_match():
    idx = DedupIndex()
    a = object()
    idx.add(a, email="  MAX@Firma.de ")
    assert idx.match(email="max@firma.de")[0] is a
