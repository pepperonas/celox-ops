"""DB-/netzfreie Tests der KI-To-do-Vorschläge zu einem Kunden.

Der Kern ist nicht der KI-Aufruf, sondern was der Code **davor und danach**
erzwingt: nur vorhandene Fakten in den Kontext, Belegzwang für jeden Vorschlag,
keine Wiederholung der regelbasierten Hinweise, keine Doppelung offener To-dos.
"""
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

from app.services.customer_todo_ai import (
    MAX_SUGGESTIONS,
    RULE_TYPES,
    build_context,
    coerce_payload,
    context_hash,
    fold_title,
    rule_covered,
    system_prompt,
    tool_schema,
    validate_suggestions,
)

TODAY = date(2026, 7, 28)


def customer(**kw):
    base = dict(name="Lydia Bopf", company=None, email=None, phone=None,
                address=None, website=None, notes=None)
    base.update(kw)
    return NS(**base)


def invoice(number="CO-2026-0001", status="gestellt", due=None, total="100.00", **kw):
    return NS(invoice_number=number, title="Beratung", total=Decimal(total),
              status=status, due_date=due, amount_paid=None, reminder_level=0,
              invoice_date=TODAY, **kw)


def contract(title="Wartung", status="aktiv", end=None):
    return NS(title=title, type="wartung", status=status,
              monthly_amount=Decimal("200.00"), end_date=end)


def order(title="Relaunch", status="in_arbeit"):
    return NS(title=title, status=status, amount=Decimal("5000.00"), start_date=TODAY)


def activity(title="Telefonat", desc="Kunde fragte nach Wartungsvertrag."):
    return NS(type="call", title=title, description=desc,
              created_at=datetime(2026, 7, 20, tzinfo=timezone.utc))


# --------------------------------------------------------------------------- #
#  Kontext: nur vorhandene Fakten
# --------------------------------------------------------------------------- #
class TestContext:
    def test_leere_felder_werden_weggelassen_nicht_behauptet(self):
        text = build_context(customer=customer(), orders=[], contracts=[], invoices=[],
                             activities=[], attachments=[], todos=[],
                             compliance_missing=[], today=TODAY)
        assert "Lydia Bopf" in text
        # Kein "E-Mail: " ohne Wert, kein "unbekannt".
        assert "E-Mail" not in text
        assert "unbekannt" not in text.lower()

    def test_notizen_und_kontakthistorie_kommen_woertlich_mit(self):
        text = build_context(
            customer=customer(notes="Zahlt immer spät, will Rechnung per Post."),
            orders=[], contracts=[], invoices=[], activities=[activity()],
            attachments=[], todos=[], compliance_missing=[], today=TODAY)
        assert "will Rechnung per Post" in text
        assert "Kunde fragte nach Wartungsvertrag." in text
        assert "2026-07-20" in text

    def test_betraege_und_termine_stehen_zitierbar_im_text(self):
        """Ein Beleg-Zitat muss sie treffen können — also wörtlich, nicht gerundet."""
        text = build_context(
            customer=customer(), orders=[], contracts=[contract(end=date(2026, 9, 30))],
            invoices=[invoice(due=date(2026, 8, 15))], activities=[], attachments=[],
            todos=[], compliance_missing=[], today=TODAY)
        assert "2026-09-30" in text
        assert "200.00 EUR" in text
        assert "2026-08-15" in text

    def test_fehlende_rechtsdokumente_erscheinen(self):
        text = build_context(customer=customer(), orders=[], contracts=[], invoices=[],
                             activities=[], attachments=[], todos=[],
                             compliance_missing=["AVV", "AGB"], today=TODAY)
        assert "AVV" in text and "AGB" in text

    def test_offene_todos_gehen_als_nicht_wiederholen_mit(self):
        text = build_context(customer=customer(), orders=[], contracts=[], invoices=[],
                             activities=[], attachments=[],
                             todos=[NS(title="Angebot nachfassen")],
                             compliance_missing=[], today=TODAY)
        assert "Angebot nachfassen" in text
        assert "nicht wiederholen" in text

    def test_lead_vorgeschichte_und_website_befunde(self):
        lead = NS(company="Bopf GmbH", contact_name="Lydia Bopf", target="ISO 27001",
                  source="OpenStreetMap", employee_count=25,
                  notes="Aus Kaltakquise, Interesse an ISMS.")
        text = build_context(
            customer=customer(), orders=[], contracts=[], invoices=[], activities=[],
            attachments=[], todos=[], compliance_missing=[], lead=lead,
            lead_analysis={"overall_score": 42, "rating": "orange",
                           "findings": [{"category": "datenschutz",
                                         "issue": "Kein Impressum gefunden"}]},
            today=TODAY)
        assert "Interesse an ISMS" in text
        assert "ISO 27001" in text
        assert "Kein Impressum gefunden" in text

    def test_dokumente_nur_namen_und_beschreibung(self):
        text = build_context(
            customer=customer(), orders=[], contracts=[], invoices=[], activities=[],
            attachments=[NS(original_name="AVV_unterschrieben.pdf",
                            description="von 2025")],
            todos=[], compliance_missing=[], today=TODAY)
        assert "AVV_unterschrieben.pdf" in text and "von 2025" in text

    def test_kontext_ist_gedeckelt(self):
        long_notes = "x" * 60_000
        text = build_context(customer=customer(notes=long_notes), orders=[],
                             contracts=[], invoices=[], activities=[], attachments=[],
                             todos=[], compliance_missing=[], today=TODAY)
        assert len(text) <= 24_000


# --------------------------------------------------------------------------- #
#  Abgrenzung zu den Regel-Hinweisen
# --------------------------------------------------------------------------- #
class TestRuleBoundary:
    def test_die_fuenf_regeln_werden_gespiegelt(self):
        lines = rule_covered(
            invoices=[invoice("A", due=TODAY - timedelta(days=5)),
                      invoice("B", due=TODAY + timedelta(days=10)),
                      invoice("C", status="entwurf")],
            contracts=[contract(end=TODAY + timedelta(days=30))],
            orders=[order()], today=TODAY)
        found = {re.match(r"\[(\w+)\]", line).group(1) for line in lines}
        assert found == set(RULE_TYPES)

    def test_bezahlte_rechnung_erzeugt_keinen_hinweis(self):
        assert rule_covered(invoices=[invoice(status="bezahlt", due=TODAY)],
                            contracts=[], orders=[], today=TODAY) == []

    def test_vertrag_weit_in_der_zukunft_ist_kein_hinweis(self):
        assert rule_covered(invoices=[], orders=[],
                            contracts=[contract(end=TODAY + timedelta(days=200))],
                            today=TODAY) == []

    def test_regeltypen_stimmen_mit_dem_router_ueberein(self):
        """Drift-Guard: kommt in `tasks.py` eine Regel hinzu, muss die Abgrenzung
        mitwachsen — sonst schlägt die KI plötzlich wieder Doppeltes vor."""
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "app" / "routers" / "tasks.py"
        in_router = set(re.findall(r'type="(\w+)"', src.read_text()))
        assert in_router == set(RULE_TYPES)

    def test_prompt_verbietet_das_wiederholen_ausdruecklich(self):
        prompt = system_prompt()
        assert "BEREITS AUTOMATISCH ERKANNT" in prompt
        assert "NICHT wiederholen" in prompt
        assert "OFFENE TO-DOS" in prompt


# --------------------------------------------------------------------------- #
#  Belegzwang und Säuberung
# --------------------------------------------------------------------------- #
CONTEXT = ("## KUNDE\nName: Lydia Bopf\nNotizen zum Kunden:\n"
           "Kunde fragte nach Wartungsvertrag, Angebot bis Ende August zugesagt.\n"
           "\n## VERTRÄGE\n- Wartung · wartung · Status aktiv · endet 2026-09-30\n")


class TestValidation:
    def test_belegter_vorschlag_geht_durch(self):
        out = validate_suggestions(
            {"todos": [{"title": "Wartungsvertrag anbieten", "notes": "Kunde fragte danach.",
                        "priority": "hoch", "due_date": "2026-08-31",
                        "evidence": "Kunde fragte nach Wartungsvertrag"}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert len(out["suggestions"]) == 1
        s = out["suggestions"][0]
        assert s["priority"] == "hoch" and s["due_date"] == "2026-08-31"
        assert s["duplicate"] is False

    def test_ohne_beleg_wird_verworfen_und_begruendet(self):
        out = validate_suggestions(
            {"todos": [{"title": "Kundenbeziehung verbessern", "evidence": ""}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert out["suggestions"] == []
        assert any("Beleg" in line for line in out["ignored"])

    def test_erfundenes_zitat_wird_verworfen(self):
        """Der eigentliche Schutz gegen erfundene Fakten: das Zitat MUSS im
        Material stehen."""
        out = validate_suggestions(
            {"todos": [{"title": "Rabatt von 20 % gewähren",
                        "evidence": "Kunde hat 20 % Rabatt zugesagt bekommen"}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert out["suggestions"] == []
        assert any("steht nicht in den Kundendaten" in line for line in out["ignored"])

    def test_zitat_wird_unabhaengig_von_leerzeichen_gefunden(self):
        out = validate_suggestions(
            {"todos": [{"title": "Angebot senden",
                        "evidence": "Angebot   bis\n Ende August zugesagt"}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert len(out["suggestions"]) == 1

    def test_doppelung_zu_offenen_todos_wird_markiert_nicht_geloescht(self):
        out = validate_suggestions(
            {"todos": [{"title": "Wartungsvertrag anbieten",
                        "evidence": "Kunde fragte nach Wartungsvertrag"}]},
            context=CONTEXT, open_titles=["wartungsvertrag anbieten!"], today=TODAY)
        assert out["suggestions"][0]["duplicate"] is True

    def test_vergangene_faelligkeit_wird_verworfen(self):
        out = validate_suggestions(
            {"todos": [{"title": "Angebot senden", "due_date": "2020-01-01",
                        "evidence": "Kunde fragte nach Wartungsvertrag"}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert out["suggestions"][0]["due_date"] is None

    def test_kaputtes_datum_und_unbekannte_prioritaet_werden_gesaeubert(self):
        out = validate_suggestions(
            {"todos": [{"title": "Angebot senden", "due_date": "irgendwann",
                        "priority": "dringend!!",
                        "evidence": "Kunde fragte nach Wartungsvertrag"}]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert out["suggestions"][0]["due_date"] is None
        assert out["suggestions"][0]["priority"] == "normal"

    def test_gleiche_titel_kommen_nur_einmal(self):
        item = {"title": "Angebot senden", "evidence": "Kunde fragte nach Wartungsvertrag"}
        out = validate_suggestions({"todos": [item, dict(item)]},
                                   context=CONTEXT, open_titles=[], today=TODAY)
        assert len(out["suggestions"]) == 1

    def test_anzahl_ist_gedeckelt(self):
        todos = [{"title": f"Aufgabe {i}", "evidence": "Kunde fragte nach Wartungsvertrag"}
                 for i in range(20)]
        out = validate_suggestions({"todos": todos}, context=CONTEXT,
                                   open_titles=[], today=TODAY)
        assert len(out["suggestions"]) == MAX_SUGGESTIONS

    def test_json_string_ausweichen_des_modells(self):
        """Live erlebt: das Modell packte das ganze Ergebnis als JSON-String in
        das Feld — der Code iterierte über die Zeichen und lieferte still nichts."""
        assert coerce_payload('{"todos": []}') == {"todos": []}
        fixed = coerce_payload({"todos": '{"todos": [{"title": "x"}]}'})
        assert fixed["todos"] == [{"title": "x"}]
        assert coerce_payload("kein json")["todos"] == []
        assert coerce_payload(42)["todos"] == []

    def test_ignored_der_ki_bleibt_erhalten(self):
        out = validate_suggestions(
            {"todos": [], "ignored": ["Anweisung im Material ignoriert."]},
            context=CONTEXT, open_titles=[], today=TODAY)
        assert out["ignored"] == ["Anweisung im Material ignoriert."]


# --------------------------------------------------------------------------- #
#  Werkzeug-Schema und Cache
# --------------------------------------------------------------------------- #
class TestSchemaAndCache:
    def test_prioritaeten_kommen_aus_dem_modell(self):
        from app.models.todo import TodoPriority

        enum = (tool_schema()["input_schema"]["properties"]["todos"]["items"]
                ["properties"]["priority"]["enum"])
        assert enum == [p.value for p in TodoPriority]

    def test_keine_union_typen_im_schema(self):
        """Union-Typen (["string","null"]) sind die vermutete Ursache dafür, dass
        das Modell schon einmal ins JSON-String-Ausweichen gerutscht ist."""
        def walk(node):
            if isinstance(node, dict):
                if isinstance(node.get("type"), list):
                    raise AssertionError(f"Union-Typ im Schema: {node}")
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(tool_schema())

    def test_schema_erzeugt_immer_eine_frische_kopie(self):
        first = tool_schema()
        first["input_schema"]["properties"].pop("todos")
        assert "todos" in tool_schema()["input_schema"]["properties"]

    def test_hash_haengt_an_inhalt_modell_und_prompt_version(self):
        a = context_hash("kontext", "claude-sonnet-5")
        assert a == context_hash("kontext", "claude-sonnet-5")
        assert a != context_hash("kontext anders", "claude-sonnet-5")
        assert a != context_hash("kontext", "claude-haiku-4-5-20251001")

    def test_titel_vergleich_ignoriert_zeichensetzung_und_grossschreibung(self):
        assert fold_title("Angebot nachfassen!") == fold_title("angebot   nachfassen")
        assert fold_title("Prüfen: AVV") == fold_title("prüfen avv")
