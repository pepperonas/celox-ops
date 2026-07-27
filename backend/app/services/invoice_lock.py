"""Unveränderlichkeit gestellter Rechnungen (GoBD).

Eine Rechnung, die das Haus verlassen hat, darf inhaltlich nicht mehr still
geändert werden — sonst weicht das beim Kunden liegende Dokument von der
gespeicherten Fassung ab, während die Rechnungsnummer gleich bleibt. Der
saubere Weg existiert in der App bereits: **Stornieren (Gutschrift) +
Duplizieren** erzeugt eine neue Rechnung mit neuer Nummer.

`DELETE` war schon abgesichert (nur Entwürfe), `PUT` nicht — diese Modul
schließt die Lücke. Rein und damit ohne DB testbar.

Bewusste Entscheidung: gesperrt wird **jedes** Feld aus `InvoiceUpdate`, denn
alle erscheinen im PDF (auch `notes` → „Hinweis:" und `service_description`).
Interne Vermerke gehören nach dem Stellen in die Aktivitäten des Kunden, nicht
in das ausgestellte Dokument.

Nicht betroffen (eigene, fachlich gewollte Endpunkte): Statuswechsel,
Zahlungseingang (`amount_paid`), Mahnstufe, PDF-Pfad — sie ändern nicht den
Rechnungsinhalt, sondern dokumentieren den Vorgang.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Status, in dem die Rechnung noch frei bearbeitbar ist.
EDITABLE_STATUS = "entwurf"

# Feldname → Bezeichnung für die Fehlermeldung (deutsch, wie im UI).
FIELD_LABELS: dict[str, str] = {
    "customer_id": "Kunde",
    "order_id": "Auftrag",
    "contract_id": "Vertrag",
    "title": "Titel",
    "positions": "Positionen",
    "tax_rate": "Steuersatz",
    "tax_exempt": "Steuerbefreiung",
    "invoice_date": "Rechnungsdatum",
    "due_date": "Fälligkeitsdatum",
    "notes": "Hinweis",
    "special_terms": "Sondervereinbarung",
    "service_description": "Leistungsbeschreibung",
    "token_usage_from": "KI-Zeitraum (von)",
    "token_usage_to": "KI-Zeitraum (bis)",
    "github_commits_from": "Commit-Zeitraum (von)",
    "github_commits_to": "Commit-Zeitraum (bis)",
    "selected_tracker_urls": "Token-Tracker-Auswahl",
    "selected_github_repos": "Repository-Auswahl",
    "include_activity_chart": "Aktivitätsdiagramm",
    "discount_type": "Rabattart",
    "discount_value": "Rabattwert",
    "discount_reason": "Rabattgrund",
}


def is_locked(status) -> bool:
    """True, sobald die Rechnung gestellt (oder weiter fortgeschritten) ist."""
    value = getattr(status, "value", status)
    return str(value) != EDITABLE_STATUS


def _norm(value):
    """Werte vergleichbar machen (Decimal/float, date/ISO-String, UUID/str).

    Nötig, weil das Request-JSON andere Typen liefert als die DB-Spalte — ohne
    Normalisierung würde ein unveränderter Wert als Änderung gelten und ein
    reiner Neu-Speichern-Klick fälschlich abgelehnt.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (Decimal, int, float)):
        return Decimal(str(value)).normalize()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return _norm_container(value)
    text = str(value).strip()
    # Zahl-in-String (Formular liefert "19.00") gegen Decimal vergleichbar machen
    try:
        return Decimal(text).normalize()
    except (InvalidOperation, ValueError):
        pass
    return text or None


def _norm_container(value):
    if isinstance(value, list):
        return [_norm_container(v) for v in value]
    if isinstance(value, dict):
        # Nur gesetzte Schlüssel vergleichen; Decimal→str für stabile Gleichheit
        return {k: str(_norm_container(v)) for k, v in sorted(value.items())
                if v is not None and v != ""}
    return _norm(value)


def changed_locked_fields(current: dict, update: dict) -> list[str]:
    """Welche inhaltlichen Felder soll der Request tatsächlich ändern?

    Vergleicht **Werte** statt nur Anwesenheit: ein Formular, das den ganzen
    Datensatz unverändert zurücksendet, läuft damit durch (idempotent), während
    jede echte Änderung erkannt wird.
    """
    changed: list[str] = []
    for field, new_value in update.items():
        if field not in FIELD_LABELS:
            continue                      # kein Inhaltsfeld → nicht gesperrt
        if _norm(new_value) != _norm(current.get(field)):
            changed.append(field)
    return changed


def lock_error(fields: list[str]) -> str:
    """Klartext-Begründung mit dem korrekten Weg (Storno + Duplizieren)."""
    labels = [FIELD_LABELS.get(f, f) for f in fields]
    what = ", ".join(labels[:4]) + (" …" if len(labels) > 4 else "")
    return (
        "Eine gestellte Rechnung darf inhaltlich nicht mehr geändert werden "
        f"(betroffen: {what}). Für eine Korrektur: „Stornieren (Gutschrift)“ und "
        "anschließend „Duplizieren“ — das erzeugt eine neue Rechnung mit neuer "
        "Nummer. Interne Vermerke gehören in die Aktivitäten des Kunden."
    )
