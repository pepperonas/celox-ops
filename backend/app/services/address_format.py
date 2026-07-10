"""Adress-Formatierung für PDF-Anschriftenblöcke (DIN-5008-nah).

Das Adressfeld ist einzeiliger Freitext — Kunden tippen
"Hauptstraße 24, 35510 Butzbach, Deutschland" oder auch ohne Kommas.
Für den Briefkopf muss daraus der übliche deutsche Anschriftenblock werden:

    Hauptstraße 24
    35510 Butzbach

Regeln:
- Mehrzeilige Eingabe (\n) → Zeilen unverändert übernehmen
- Kommasepariert → an Kommas trennen
- Einzeilig ohne Komma → vor der 5-stelligen PLZ trennen
  ("Max-Planck-Straße 5a 60486 Frankfurt am Main" →
   ["Max-Planck-Straße 5a", "60486 Frankfurt am Main"])
- Bindestriche (Straßen, Orte, Hausnummern-Bereiche wie "5-7") bleiben intakt
- Ein reines Länder-Schlusselement "Deutschland"/"Germany" entfällt
  (bei Inlandspost unüblich); andere Länder bleiben als eigene Zeile.
"""
import re

_PLZ_RE = re.compile(r"\b\d{5}\s+\S")
_DOMESTIC = {"deutschland", "germany", "de", "brd"}


def format_address_lines(address: str | None) -> list[str]:
    if not address or not address.strip():
        return []
    text = address.strip()

    if "\n" in text:
        lines = [ln.strip().rstrip(",") for ln in text.splitlines()]
    elif "," in text:
        lines = [part.strip() for part in text.split(",")]
    else:
        m = _PLZ_RE.search(text)
        if m and m.start() > 0:
            lines = [text[: m.start()].strip(), text[m.start():].strip()]
        else:
            lines = [text]

    lines = [ln for ln in lines if ln]
    # Reines "Deutschland" am Ende weglassen (Inlandspost)
    if len(lines) > 1 and lines[-1].strip().lower() in _DOMESTIC:
        lines = lines[:-1]
    return lines
