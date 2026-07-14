"""Automatische Lead-Suche für Rainmaker (celox ops).

Quellen:
- **OpenStreetMap / Overpass** (Standard, kostenlos, kein Key): findet lokale
  Firmen nach Branche (OSM-Tag) + Ort mit Name/Website/E-Mail/Telefon/Adresse.
- **Google Places** (optional, nur wenn GOOGLE_PLACES_API_KEY gesetzt):
  Text-Suche → pro Treffer ein Place-Details-Call für Website/Telefon/Status.

**Datenqualität (2026-07, „keine Karteileichen"):** Jeder zurückgegebene
Kandidat MUSS eine **Website** haben und die Website muss **live erreichbar**
sein (HTTP-Check). Zusätzlich:
- OSM verlangt **Website UND E-Mail** (OSM kann beides liefern → Top-Qualität).
- Google verlangt **Website** (aus Place Details) und **business_status =
  OPERATIONAL** (Googles Signal gegen dauerhaft/temporär geschlossene Betriebe).
  E-Mail liefert die Google Places API grundsätzlich nicht → bleibt None.

Reine Bausteine (Query-Bau, Parsing, Filter, URL-Normalisierung) sind netzfrei
testbar; die HTTP-Aufrufe (Overpass, Google, Live-Check) laufen async über einen
injizierten httpx-Client.
"""
import asyncio
import re

import httpx

# Overpass-Server in Fallback-Reihenfolge: primär offiziell, dann ein
# unabhängiger Mirror (CH), dann eine weitere Instanz. Bei Überlastung (504)
# eines Servers wird der nächste versucht. (kumi/private.coffee sind von der
# VPS-IP nicht erreichbar → bewusst nicht gelistet.)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]
OVERPASS_URL = OVERPASS_ENDPOINTS[0]   # Rückwärtskompatibilität
# Transiente Overpass-Antworten → nächster Server (statt hartem Fehler).
_OVERPASS_TRANSIENT = {429, 500, 502, 503, 504}

GOOGLE_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
# Nur die Felder, die wir wirklich brauchen — hält den Details-Call günstig.
GOOGLE_DETAILS_FIELDS = "website,formatted_phone_number,business_status"

# Segment → OSM-Tags (Union). Deckt 4 der 5 celox-Segmente lokal gut ab;
# reines E-Commerce ist über OSM nicht sinnvoll findbar (keine Kartenobjekte).
SEGMENT_OSM_TAGS: dict[str, list[str]] = {
    "hausverwaltung": ["office=property_management"],
    "steuerkanzlei": ["office=tax_advisor", "office=accountant"],
    "makler_finanzberater": ["office=insurance", "office=financial_advisor", "office=estate_agent"],
    "agentur": ["office=advertising_agency", "office=it"],
    "anwalt": ["office=lawyer"],
    "arzt_praxis": ["amenity=doctors", "amenity=dentist"],
    "handwerk": ["craft=carpenter", "craft=electrician", "craft=plumber"],
}

# Menschenlesbare Labels für die Vorschau/Chips.
SEGMENT_LABELS = {
    "hausverwaltung": "Hausverwaltung",
    "steuerkanzlei": "Steuerkanzlei",
    "makler_finanzberater": "Makler / Finanzberater",
    "agentur": "Agentur / IT-Dienstleister",
    "anwalt": "Anwaltskanzlei",
    "arzt_praxis": "Arzt-/Zahnarztpraxis",
    "handwerk": "Handwerksbetrieb",
}


def _sanitize(value: str) -> str:
    """Anführungszeichen/Backslashes raus — verhindert Query-Injection in Overpass QL."""
    return (value or "").replace('"', "").replace("\\", "").strip()


def normalize_url(url: str | None) -> str | None:
    """Trimmt, ergänzt fehlendes Schema (→ https://) und prüft grob auf einen Host.
    Rückgabe None, wenn leer oder offensichtlich keine Domain (kein Punkt im Host)."""
    u = (url or "").strip()
    if not u:
        return None
    if not re.match(r"^https?://", u, re.IGNORECASE):
        u = "https://" + u
    try:
        host = u.split("://", 1)[1].split("/", 1)[0].split("?", 1)[0]
    except IndexError:
        return None
    host = host.split("@")[-1].split(":")[0]  # user@ und :port abtrennen
    if "." not in host or host.startswith(".") or host.endswith("."):
        return None
    return u


def _clean_email(value: str | None) -> str | None:
    """Erste plausible E-Mail aus einem OSM-Feld (kann mehrere ;-getrennte enthalten)."""
    v = (value or "").strip()
    if not v:
        return None
    first = re.split(r"[;, ]", v)[0].strip()
    return first if "@" in first and "." in first.split("@")[-1] else None


def resolve_tags(category: str) -> list[str]:
    """category = Segment-Key ODER roher OSM-Tag 'key=value'. Rückgabe: Tag-Liste."""
    if category in SEGMENT_OSM_TAGS:
        return SEGMENT_OSM_TAGS[category]
    if "=" in category:
        k, v = category.split("=", 1)
        if k.strip() and v.strip():
            return [f"{_sanitize(k)}={_sanitize(v)}"]
    raise ValueError(f"Unbekannte Branche/Tag: {category!r}")


def build_overpass_query(tags: list[str], location: str, limit: int = 60) -> str:
    """Overpass-QL: alle Objekte mit einem der Tags im benannten Gebiet."""
    loc = _sanitize(location)
    limit = max(1, min(int(limit), 200))
    filters = ""
    for t in tags:
        k, _, v = t.partition("=")
        filters += f'nwr["{_sanitize(k)}"="{_sanitize(v)}"](area.a);'
    return (
        f'[out:json][timeout:25];'
        f'area["name"="{loc}"]->.a;'
        f'({filters});'
        f'out center tags {limit};'
    )


def parse_overpass(data: dict) -> list[dict]:
    """Overpass-JSON → Kandidaten (alle mit Name). Website wird normalisiert, E-Mail
    extrahiert. Die Qualitätsfilterung (Website+E-Mail) passiert separat."""
    out: list[dict] = []
    seen: set[str] = set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        website = normalize_url(tags.get("website") or tags.get("contact:website"))
        email = _clean_email(tags.get("email") or tags.get("contact:email"))
        phone = tags.get("phone") or tags.get("contact:phone") or None
        street = " ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber")) if p)
        cityline = " ".join(p for p in (tags.get("addr:postcode"), tags.get("addr:city")) if p)
        address = ", ".join(p for p in (street, cityline) if p) or None
        out.append({
            "name": name, "website": website, "email": email, "phone": phone,
            "address": address, "source": "OpenStreetMap",
            "source_ref": f"{el.get('type')}/{el.get('id')}",
        })
    return out


def filter_osm_quality(rows: list[dict]) -> list[dict]:
    """OSM-Qualitätsregel: nur Kandidaten mit Website UND E-Mail."""
    return [r for r in rows if r.get("website") and r.get("email")]


async def website_alive(url: str | None, client, timeout: float = 4.0) -> bool:
    """True, wenn die Website eine Antwort < 400 liefert (Redirects werden verfolgt).
    Erst HEAD (billig), bei Ablehnung GET als Fallback. Jeder Fehler → False."""
    u = normalize_url(url)
    if not u:
        return False
    for method in ("head", "get"):
        try:
            resp = await getattr(client, method)(u, follow_redirects=True, timeout=timeout)
        except Exception:
            continue
        code = getattr(resp, "status_code", 599)
        if code < 400:
            return True
        # Viele Server lehnen HEAD ab (403/405/501) → mit GET nachfassen.
        if method == "head" and code in (400, 401, 403, 404, 405, 406, 501):
            continue
        return False
    return False


async def filter_live_websites(rows: list[dict], client, concurrency: int = 8,
                               timeout: float = 4.0) -> list[dict]:
    """Behält nur Kandidaten, deren Website live erreichbar ist (parallel geprüft)."""
    if not rows:
        return rows
    sem = asyncio.Semaphore(max(1, concurrency))

    async def check(row: dict) -> bool:
        async with sem:
            return await website_alive(row.get("website"), client, timeout)

    results = await asyncio.gather(*(check(r) for r in rows))
    return [r for r, ok in zip(rows, results) if ok]


async def _overpass_query(query: str, client) -> dict:
    """POST an Overpass mit **Mirror-Fallback**: bei Überlastung (429/5xx) oder
    Timeout/Connect-Fehler wird der nächste Server versucht. Erst wenn ALLE
    ausfallen → ValueError mit klarer Meldung (der Router meldet sie als 422).
    Ein echter Fehler (z. B. 400 = kaputte Query) bricht sofort ab."""
    last: Exception | None = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = await client.post(url, data={"data": query})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            last = exc
            if exc.response.status_code not in _OVERPASS_TRANSIENT:
                raise ValueError(f"Overpass-Anfrage abgelehnt (HTTP {exc.response.status_code}).") from exc
            # transient → nächster Server
        except httpx.RequestError as exc:      # Timeout/Connect/Read → nächster Server
            last = exc
    raise ValueError(
        "OpenStreetMap/Overpass ist gerade überlastet — alle Server antworten mit "
        "Timeout/Fehler. Bitte in ein paar Minuten erneut versuchen oder Google Places nutzen."
    ) from last


async def discover_osm(category: str, location: str, limit, client) -> list[dict]:
    query = build_overpass_query(resolve_tags(category), location, limit)
    data = await _overpass_query(query, client)
    rows = filter_osm_quality(parse_overpass(data))          # Website + E-Mail Pflicht
    return await filter_live_websites(rows, client)          # tote Domains raus


# Google-Text-Search-Status, die kein echtes Ergebnis sind → als Fehler melden.
_GOOGLE_OK = {"OK", "ZERO_RESULTS"}


def _google_status_guard(status: str | None) -> None:
    if status and status not in _GOOGLE_OK:
        if status == "REQUEST_DENIED":
            raise ValueError("Google Places lehnt den Key ab (Key/Places-API/Abrechnung prüfen)")
        if status == "OVER_QUERY_LIMIT":
            raise ValueError("Google-Kontingent erschöpft")
        if status == "NOT_FOUND":       # nur bei Details relevant → kein harter Fehler
            return
        raise ValueError(f"Google Places: {status}")


def parse_google(data: dict, limit: int) -> list[dict]:
    """Text-Search-JSON → Roh-Kandidaten. Filtert dauerhaft/temporär geschlossene
    Betriebe (business_status != OPERATIONAL) direkt heraus. Website/E-Mail liefert
    die Text-Suche nicht — die kommen aus dem Place-Details-Call."""
    _google_status_guard(data.get("status"))
    out: list[dict] = []
    for res in (data.get("results") or []):
        if len(out) >= limit:
            break
        name = (res.get("name") or "").strip()
        if not name:
            continue
        bs = res.get("business_status")
        if bs and bs != "OPERATIONAL":   # geschlossen → Karteileiche, raus
            continue
        out.append({
            "name": name, "website": None, "email": None, "phone": None,
            "address": res.get("formatted_address"),
            "source": "Google Places", "source_ref": res.get("place_id"),
            "_place_id": res.get("place_id"), "_business_status": bs,
        })
    return out


def parse_place_details(data: dict) -> dict:
    """Place-Details-JSON → {website, phone, business_status}. Website normalisiert.
    REQUEST_DENIED/OVER_QUERY_LIMIT werfen (Key-/Quota-Problem); NOT_FOUND → leer."""
    _google_status_guard(data.get("status"))
    result = data.get("result") or {}
    return {
        "website": normalize_url(result.get("website")),
        "phone": result.get("formatted_phone_number"),
        "business_status": result.get("business_status"),
    }


async def discover_google(category: str, location: str, limit, api_key: str,
                          client) -> tuple[list[dict], int]:
    """Text-Suche + Place-Details je Treffer. Website Pflicht, business_status muss
    OPERATIONAL sein, Website live erreichbar. Rückgabe: (Kandidaten, API-Call-Anzahl)
    — der Router zählt damit den Nutzungszähler korrekt hoch."""
    label = SEGMENT_LABELS.get(category, category)
    resp = await client.get(GOOGLE_TEXTSEARCH_URL, params={
        "query": f"{label} in {location}", "key": api_key, "language": "de",
    })
    resp.raise_for_status()
    rows = parse_google(resp.json(), max(1, min(int(limit), 60)))
    api_calls = 1

    enriched: list[dict] = []
    for r in rows:
        pid = r.pop("_place_id", None)
        r.pop("_business_status", None)
        if not pid:
            continue
        dresp = await client.get(GOOGLE_DETAILS_URL, params={
            "place_id": pid, "fields": GOOGLE_DETAILS_FIELDS, "key": api_key, "language": "de",
        })
        dresp.raise_for_status()
        api_calls += 1
        det = parse_place_details(dresp.json())
        status = det.get("business_status")
        if status and status != "OPERATIONAL":
            continue
        if not det.get("website"):        # Website Pflicht — ohne sie kein Lead
            continue
        r["website"] = det["website"]
        r["phone"] = det.get("phone") or r.get("phone")
        enriched.append(r)

    enriched = await filter_live_websites(enriched, client)
    return enriched, api_calls
