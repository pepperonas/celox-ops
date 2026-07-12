"""Automatische Lead-Suche für Rainmaker (celox ops).

Quellen:
- **OpenStreetMap / Overpass** (Standard, kostenlos, kein Key): findet lokale
  Firmen nach Branche (OSM-Tag) + Ort mit Name/Website/Telefon/Adresse.
- **Google Places** (optional, nur wenn GOOGLE_PLACES_API_KEY gesetzt):
  Text-Suche, liefert Name + Adresse.

Reine Bausteine (Query-Bau, Parsing) sind netzfrei testbar; die eigentlichen
HTTP-Aufrufe laufen async über einen injizierten httpx-Client.
"""
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GOOGLE_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

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
    """Overpass-JSON → Kandidaten. Ohne Name kein Kandidat (company ist NOT NULL)."""
    out: list[dict] = []
    seen: set[str] = set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        website = tags.get("website") or tags.get("contact:website") or None
        phone = tags.get("phone") or tags.get("contact:phone") or None
        street = " ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber")) if p)
        cityline = " ".join(p for p in (tags.get("addr:postcode"), tags.get("addr:city")) if p)
        address = ", ".join(p for p in (street, cityline) if p) or None
        out.append({
            "name": name, "website": website, "phone": phone, "address": address,
            "source": "OpenStreetMap", "source_ref": f"{el.get('type')}/{el.get('id')}",
        })
    return out


async def discover_osm(category: str, location: str, limit, client) -> list[dict]:
    query = build_overpass_query(resolve_tags(category), location, limit)
    resp = await client.post(OVERPASS_URL, data={"data": query})
    resp.raise_for_status()
    return parse_overpass(resp.json())


def parse_google(data: dict, limit: int) -> list[dict]:
    out = []
    for res in (data.get("results") or [])[:limit]:
        name = (res.get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name, "website": None, "phone": None,
            "address": res.get("formatted_address"),
            "source": "Google Places", "source_ref": res.get("place_id"),
        })
    return out


async def discover_google(category: str, location: str, limit, api_key: str, client) -> list[dict]:
    label = SEGMENT_LABELS.get(category, category)
    resp = await client.get(GOOGLE_TEXTSEARCH_URL, params={
        "query": f"{label} in {location}", "key": api_key, "language": "de",
    })
    resp.raise_for_status()
    return parse_google(resp.json(), max(1, min(int(limit), 60)))
