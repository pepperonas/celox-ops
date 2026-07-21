"""DB-freie Tests für den Lead-Trefferbau der globalen Suche."""
import uuid
from types import SimpleNamespace

from app.models.rainmaker_lead import RainmakerLeadStatus
from app.routers.search import _LEAD_STATUS_LABELS, lead_hit
from app.services.taxonomy import TAXONOMIES


def _lead(**over):
    base = dict(
        id=uuid.uuid4(), company="Beispiel GmbH", contact_name=None,
        target=None, status=RainmakerLeadStatus.new,
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestLeadHit:
    def test_links_to_lead_detail_not_removed_route(self):
        # Regression: früher zeigte jeder Lead-Treffer auf /vorgemerkt (entfernt)
        lead = _lead()
        hit = lead_hit(lead)
        assert hit.url == f"/pipeline/leads/{lead.id}"
        assert "vorgemerkt" not in hit.url

    def test_title_is_company_and_type_is_lead(self):
        hit = lead_hit(_lead(company="A2 Doku GmbH"))
        assert hit.title == "A2 Doku GmbH"
        assert hit.type == "lead"

    def test_subtitle_has_contact_target_and_german_status(self):
        hit = lead_hit(_lead(contact_name="Manfred Schüller", target="bcs / zeiterfassung"))
        assert hit.subtitle == "Manfred Schüller · bcs / zeiterfassung · Neu"

    def test_subtitle_falls_back_to_status_only(self):
        assert lead_hit(_lead()).subtitle == "Neu"

    def test_all_statuses_have_german_labels(self):
        # Jeder Enum-Wert braucht ein Label — sonst stünde der technische
        # englische Wert im Untertitel.
        for status in RainmakerLeadStatus:
            assert status.value in _LEAD_STATUS_LABELS, status
            assert lead_hit(_lead(status=status)).subtitle == _LEAD_STATUS_LABELS[status.value]

    def test_accepts_plain_string_status(self):
        # falls das ORM den Enum als String liefert
        assert lead_hit(_lead(status="won")).subtitle == "Gewonnen"

    def test_id_is_stringified(self):
        assert isinstance(lead_hit(_lead()).id, str)


class TestDsmsTodoEntries:
    def test_handoff_entry_removed(self):
        # Die technische Übergabe ist ein Button, keine planbare Aufgabe
        assert "Kunde an datenschutz.celox.io übergeben" not in TAXONOMIES["todo"]

    def test_selling_entries_present(self):
        todos = TAXONOMIES["todo"]
        assert "Datenschutz-Plattform beim Kunden ansprechen" in todos
        assert "DSMS-Demo vereinbaren" in todos
        assert "Datenschutz-Plattform als Zusatzleistung anbieten" in todos
