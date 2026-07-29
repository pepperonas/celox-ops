"""Aufsicht über die Lead-Arbeit zugeschnittener Rollen — reine, testbare Logik.

Drei Bausteine, alle ohne DB und ohne Request:
  * `diff_fields`     — was hat sich bei einem Speichern tatsächlich geändert?
  * `revert_plan`     — welche Felder darf eine Rücknahme zurücksetzen?
  * `delete_cap_left` — wie viele Löschungen bleiben heute?

Die DB-Arbeit (Zeilen laden, schreiben) liegt im Router; hier steht, WAS gilt.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

# Felder, die im Protokoll auftauchen und zurückgenommen werden können.
# Bewusst eine Whitelist: Ein Protokoll über `updated_at` oder `email_norm`
# (generierte Spalte) wäre Rauschen, und eine Rücknahme darauf wäre schlicht
# falsch. Deckt die Felder ab, die ein Mensch im Formular pflegt.
TRACKED_FIELDS: tuple[str, ...] = (
    "company", "contact_name", "role", "email", "phone", "website",
    "source", "status", "priority", "target", "notes", "tags",
    "employee_count", "decision_maker", "value_estimate", "pinned",
)


def _plain(value: Any) -> Any:
    """JSON-fähige Fassung eines Feldwerts (die Spalte ist JSON).

    Decimal und date/datetime kommen aus den Lead-Spalten und sind nicht
    JSON-serialisierbar — als String bleiben sie vergleichbar UND anzeigbar.
    Enums (Status, Priorität) werden auf ihren Wert reduziert.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return getattr(value, "value", str(value))


def diff_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Nur die Felder, die sich WIRKLICH geändert haben.

    Ein Formular sendet meist alle Felder zurück. Würde man alles protokollieren,
    wäre jede Statusänderung ein 16-Feld-Eintrag und die Rücknahme würde
    unbeteiligte Felder mit zurückdrehen.
    """
    out: dict[str, dict[str, Any]] = {}
    for field in TRACKED_FIELDS:
        if field not in after:
            continue
        old, new = _plain(before.get(field)), _plain(after.get(field))
        if old != new:
            out[field] = {"old": old, "new": new}
    return out


def revert_plan(
    changes: dict[str, dict[str, Any]], current: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Was eine Rücknahme setzen darf — und was sie liegen lassen muss.

    Zurückgesetzt wird ein Feld nur, wenn es **noch auf dem protokollierten neuen
    Wert steht**. Hat inzwischen jemand anders daran gearbeitet, würde die
    Rücknahme dessen Arbeit stillschweigend überschreiben; solche Felder werden
    stattdessen als Konflikt gemeldet.

    Rückgabe: (zu setzende Werte, Namen der übersprungenen Felder)
    """
    apply: dict[str, Any] = {}
    conflicts: list[str] = []
    for field, pair in changes.items():
        if field not in TRACKED_FIELDS:
            continue          # unbekanntes Feld nie blind zurückschreiben
        if _plain(current.get(field)) == pair.get("new"):
            apply[field] = pair.get("old")
        else:
            conflicts.append(field)
    return apply, conflicts


def delete_cap_left(used_today: int, cap: int) -> int:
    """Wie viele Löschungen bleiben heute? Nie negativ."""
    return max(0, cap - max(0, used_today))


def cap_message(cap: int) -> str:
    return (
        f"Das Tageslimit von {cap} Löschungen ist erreicht. "
        "Weitere Leads kann der Kontoinhaber entfernen — "
        "bereits gelöschte liegen im Papierkorb."
    )
