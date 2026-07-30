"""Referenzkunden anreichern: Website auflösen, dann Impressum lesen.

Aus der Logo-Wand kommt nur ein Name. Für Geschäftsführung, Telefon und E-Mail
braucht es das **Impressum**, und dafür die **Website** — die haben wir bei 10 von
3.712. Diese Datei schließt genau diese Lücke, in zwei Schritten:

  1. **Name → Website** über Google Places (kostet pro Abfrage, deshalb nur auf
     ausdrückliche Anforderung und für eine ausgewählte Spitze).
  2. **Website → Impressum** über die vorhandene, deterministische Extraktion
     (`market_contacts`) — kostenlos, und jeder Wert ist eine wörtliche
     Teilzeichenfolge der abgerufenen Seite.

**Die Namensprüfung ist der kritische Teil.** Eine Places-Textsuche nach einem
Firmennamen liefert bereitwillig eine *ähnlich* heißende Firma — „Tetra GmbH"
(Fischfutter, Melle) und „Tetra Pak Deutschland GmbH" sind nicht dasselbe. Eine
falsche Website ist schlimmer als keine: Sie führt zu einem falschen Impressum, also
zu einem falschen Geschäftsführer und einer falschen Telefonnummer. Deshalb gilt
`namen_passen` streng und lässt im Zweifel nichts durch.
"""
from __future__ import annotations

import re

from app.models.market_reference import norm_company
from app.services.lead_discovery import (
    GOOGLE_DETAILS_FIELDS,
    GOOGLE_DETAILS_URL,
    GOOGLE_TEXTSEARCH_URL,
    parse_google,
    parse_place_details,
)

# Rechtsformen und Ortszusätze zählen nicht als aussagekräftiges Namenswort: Sie
# kommen in tausenden Namen vor und würden zwei fremde Firmen „übereinstimmen" lassen.
_UNBEDEUTEND = {
    "gmbh", "ggmbh", "mbh", "ag", "kg", "kgaa", "ohg", "gbr", "ug", "se", "eg", "ev",
    "ek", "co", "und", "the", "group", "gruppe", "holding", "deutschland", "germany",
    "international", "gmbhcokg", "sa", "bv", "nv", "ltd", "inc", "llc", "plc",
}


def _bedeutsame_woerter(name: str) -> list[str]:
    """Namensbestandteile, die eine Firma tatsächlich unterscheiden. Rein."""
    roh = re.split(r"[^A-Za-zÄÖÜäöüß0-9]+", (name or "").lower())
    return [w for w in roh if len(w) >= 3 and w not in _UNBEDEUTEND]


def namen_passen(gesucht: str, gefunden: str) -> bool:
    """Ist die von Places gefundene Firma die gesuchte? Rein — und absichtlich streng.

    Drei Stufen:

      1. Normalisiert gleich → ja.
      2. Beide haben **mindestens zwei** aussagekräftige Wörter, und alle des kürzeren
         Namens stecken im längeren → ja („Stadtwerke Achim" ⊂ „Stadtwerke Achim AG",
         „Julius Zorn" ⊂ „Julius Zorn GmbH Juzo").
      3. Sonst nein.

    **Warum Stufe 2 zwei Wörter verlangt:** Mit einem einzigen Wort wäre „Tetra GmbH"
    eine Übereinstimmung mit „Tetra Pak Deutschland GmbH" — verschiedene Firmen. Der
    Preis ist, dass einwortige Namen („Anschütz GmbH" vs. „Raytheon Anschütz GmbH")
    abgelehnt werden, obwohl sie oft stimmen. Das ist der gewollte Handel: lieber
    keine Website als die falsche, denn aus der falschen folgt ein falscher
    Geschäftsführer.
    """
    if not (gesucht or "").strip() or not (gefunden or "").strip():
        return False
    if norm_company(gesucht) == norm_company(gefunden):
        return True
    a, b = _bedeutsame_woerter(gesucht), _bedeutsame_woerter(gefunden)
    if len(a) < 2 or len(b) < 2:
        return False
    kurz, lang = (a, b) if len(a) <= len(b) else (b, a)
    return all(w in lang for w in kurz)


async def resolve_website(
    company: str, api_key: str, client, *, region: str = "Deutschland",
) -> tuple[dict | None, int]:
    """Firmenname → {website, phone, address, places_name} oder None.

    Rückgabe zusätzlich die Anzahl der **echten** API-Abfragen, damit der
    Nutzungszähler stimmt (Places rechnet Textsuche und Details getrennt ab).

    Geprüft wird der erste Treffer, dessen Name die Namensprüfung besteht — nicht
    einfach der erste: Die Textsuche sortiert nach ihrer eigenen Relevanz, und die
    kennt unsere Firma nicht.
    """
    resp = await client.get(GOOGLE_TEXTSEARCH_URL, params={
        "query": f"{company} {region}".strip(), "key": api_key, "language": "de",
    })
    resp.raise_for_status()
    kandidaten = parse_google(resp.json(), 5)
    calls = 1

    for k in kandidaten:
        if not namen_passen(company, k.get("name") or ""):
            continue
        pid = k.get("_place_id")
        if not pid:
            continue
        d = await client.get(GOOGLE_DETAILS_URL, params={
            "place_id": pid, "fields": GOOGLE_DETAILS_FIELDS, "key": api_key,
            "language": "de",
        })
        d.raise_for_status()
        calls += 1
        det = parse_place_details(d.json())
        if det.get("business_status") and det["business_status"] != "OPERATIONAL":
            continue
        if not det.get("website"):
            continue
        return {
            "website": det["website"],
            "phone": det.get("phone"),
            "address": k.get("address"),
            "places_name": k.get("name"),
        }, calls
    return None, calls
