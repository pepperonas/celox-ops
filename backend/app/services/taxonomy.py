"""Zentrale Taxonomie für App-weite Autocomplete-Vorschläge (hybrid).

EINE kanonische Quelle: kuratierte deutsche Listen pro Feld-Key + Synonym-Mapping
auf die kanonische Schreibweise. Der Suggestions-Endpoint mischt die kuratierten
Werte mit den eigenen Bestandswerten des Owners (DISTINCT, häufigkeitssortiert).

Alle Funktionen hier sind rein (kein DB-Zugriff) → DB-frei testbar.
"""
from __future__ import annotations

import unicodedata

# --------------------------------------------------------------------------- #
#  Kuratierte Listen (alphabetisch je Kategorie, dedupliziert via dict.fromkeys)
# --------------------------------------------------------------------------- #

_ROLE = [
    # ── Leitung / Inhaberschaft ──
    "Geschäftsführung",
    "Inhaber/in",
    "Vorstand",
    "Gesellschafter/in",
    "Prokurist/in",
    "Partner/in",
    "Betriebsleitung",
    "Niederlassungsleitung",
    "Filialleitung",
    "Kanzleileitung",
    "Praxisleitung",
    "Werkstattleitung",
    # ── IT / Technik ──
    "IT-Leitung",
    "CTO",
    "CIO",
    "CISO",
    "IT-Administrator/in",
    "IT-Sicherheitsbeauftragte/r",
    "Datenschutzbeauftragte/r",
    "Technische Leitung",
    "Leitung Digitalisierung",
    "Softwareentwickler/in",
    "Systemadministrator/in",
    # ── Kaufmännisch ──
    "CFO",
    "COO",
    "Kaufmännische Leitung",
    "Leitung Buchhaltung",
    "Leitung Controlling",
    "Leitung Finanzen",
    "Office Management",
    "Assistenz der Geschäftsführung",
    # ── Marketing / Vertrieb ──
    "Marketing-Leitung",
    "Vertriebsleitung",
    "Leitung E-Commerce",
    "Leitung Kommunikation",
    "Projektleitung",
    "Produktmanagement",
    # ── HR / Verwaltung ──
    "Personalleitung",
    "Leitung Einkauf",
    "Leitung Qualitätsmanagement",
    "Verwaltungsleitung",
]

_SOURCE = [
    # ── Aktive Akquise ──
    "Kaltakquise Telefon",
    "Kaltakquise E-Mail",
    "Kaltakquise vor Ort",
    "LinkedIn",
    "LinkedIn-Import",
    "XING",
    # ── Automatisiert / Recherche ──
    "KI-Recherche",
    "OpenStreetMap",
    "Google Places",
    "Recherche",
    "Branchenverzeichnis",
    "Google Maps",
    # ── Inbound ──
    "Website-Anfrage",
    "Kontaktformular",
    "Newsletter",
    "Google-Suche (Inbound)",
    "Social Media",
    # ── Netzwerk / Persönlich ──
    "Empfehlung",
    "Empfehlung Bestandskunde",
    "Empfehlung Partner",
    "Bestandskunde",
    "Netzwerk-Event",
    "Messe",
    "IHK-Veranstaltung",
    "BNI / Unternehmernetzwerk",
    "Meetup / Konferenz",
    "Stammtisch",
    "Persönlicher Kontakt",
    "Ehemaliger Kollege",
    "Ausschreibung",
    "Ausschreibungsplattform",
    "Freelancer-Plattform",
]

_BRANCHE = [
    # ── Beratung / Recht / Finanzen ──
    "Steuerberater",
    "Wirtschaftsprüfer",
    "Rechtsanwalt",
    "Notariat",
    "Unternehmensberatung",
    "Finanzberater",
    "Versicherungsmakler",
    "Immobilienmakler",
    "Hausverwaltung",
    "Facility Management",
    # ── Gesundheit / Soziales ──
    "Arztpraxis",
    "Zahnarztpraxis",
    "Physiotherapie",
    "Apotheke",
    "Pflegedienst",
    "Kita / Kindergarten",
    "Bildungsträger",
    "Verein / Non-Profit",
    # ── Handwerk / Bau ──
    "Handwerksbetrieb",
    "Bauunternehmen",
    "Elektroinstallation",
    "Sanitär / Heizung / Klima",
    "Schreinerei / Tischlerei",
    "Malerbetrieb",
    "Dachdeckerei",
    "Gebäudereinigung",
    "Garten- und Landschaftsbau",
    "Architekturbüro",
    "Ingenieurbüro",
    # ── Handel / Gastronomie ──
    "Einzelhandel",
    "Großhandel",
    "E-Commerce / Onlineshop",
    "Gastronomie",
    "Hotellerie",
    "Bäckerei",
    "Autohaus",
    "KFZ-Werkstatt",
    # ── Industrie / Logistik ──
    "Maschinenbau",
    "Fertigung / Produktion",
    "Logistik / Spedition",
    "Landwirtschaft",
    # ── Dienstleistung / Digital ──
    "Agentur / IT-Dienstleister",
    "Werbeagentur",
    "Softwareunternehmen",
    "Personaldienstleister",
    "Reinigungsunternehmen",
    "Sicherheitsdienst",
    "Fahrschule",
    "Fitnessstudio",
    "Friseursalon",
    "Kosmetikstudio",
    "Fotostudio",
    "Eventagentur",
    "Reisebüro",
]

# Lead-Tags = Branchen + Qualifizierer (Board-Filter, Kampagnen)
_TAG = list(dict.fromkeys([
    *_BRANCHE[:20],
    # ── Qualifizierer ──
    "Bestandskunde",
    "Neukunde",
    "lokal",
    "Berlin",
    "deutschlandweit",
    "Webshop",
    "WordPress",
    "Kleinunternehmen",
    "Mittelstand",
    "Konzern",
    "Premium",
    "Preissensibel",
    "Warmkontakt",
    "Kaltkontakt",
    "Wiedervorlage",
    "Security-Interesse",
    "DSGVO",
    "KI-Automatisierung",
    "Website-Relaunch",
    "Wartungsvertrag",
    "Empfehlungsgeber",
    "Multiplikator",
]))

_ZIELSYSTEM = [
    # ── Buchhaltung / Steuer ──
    "DATEV",
    "DATEV Unternehmen online",
    "Lexware",
    "lexoffice",
    "sevDesk",
    "BuchhaltungsButler",
    "Candis",
    "GetMyInvoices",
    # ── ERP ──
    "SAP Business One",
    "Microsoft Dynamics 365",
    "Microsoft Dynamics NAV / Business Central",
    "Odoo",
    "weclapp",
    "Xentral",
    "JTL-Wawi",
    "plentymarkets",
    "Sage 100",
    "Sage 50",
    # ── CRM ──
    "HubSpot",
    "Salesforce",
    "Pipedrive",
    "Zoho CRM",
    "CentralStationCRM",
    # ── Office / Kollaboration ──
    "Microsoft 365",
    "SharePoint",
    "Google Workspace",
    "Nextcloud",
    "Notion",
    "Confluence",
    # ── Branchen-Software ──
    "Immoware24",
    "DOMUS",
    "Haufe PowerHaus",
    "Praxissoftware (PVS)",
    "Kanzleisoftware (RA-MICRO)",
    "Handwerkersoftware (Mos'aik)",
]

_VENDOR = [
    # ── Hosting / Cloud ──
    "Hetzner",
    "IONOS",
    "Strato",
    "netcup",
    "all-inkl",
    "Hostinger",
    "AWS",
    "Google Cloud",
    "Microsoft Azure",
    "DigitalOcean",
    "Cloudflare",
    "Vercel",
    "Netlify",
    # ── Software / SaaS ──
    "Microsoft 365",
    "Google Workspace",
    "Adobe",
    "JetBrains",
    "GitHub",
    "GitLab",
    "Atlassian",
    "Notion",
    "Slack",
    "Zoom",
    "1Password",
    "Figma",
    # ── KI ──
    "Anthropic",
    "OpenAI",
    "Cursor",
    # ── Telekommunikation ──
    "Telekom",
    "Vodafone",
    "o2 / Telefónica",
    "1&1",
    "sipgate",
    # ── Büro / Betrieb ──
    "Amazon",
    "Amazon Business",
    "Conrad",
    "Galaxus",
    "Reichelt",
    "IKEA",
    "OBI / Baumarkt",
    "Deutsche Post",
    "DHL",
    "Deutsche Bahn",
    "Tankstelle",
    "REWE / Supermarkt",
    # ── Versicherung / Beiträge ──
    "IHK",
    "Berufshaftpflicht",
    "Krankenversicherung",
    "Rentenversicherung",
]

_TAETIGKEIT = [
    # ── Entwicklung ──
    "Frontend-Entwicklung",
    "Backend-Entwicklung",
    "Fullstack-Entwicklung",
    "API-Entwicklung",
    "Datenbankentwicklung",
    "App-Entwicklung",
    "Schnittstellenentwicklung",
    "Plugin-Entwicklung",
    "Skript-Entwicklung / Automatisierung",
    "Code-Review",
    "Refactoring",
    "Bugfixing",
    "Testing / QA",
    "Deployment / Release",
    # ── Website ──
    "Website-Erstellung",
    "Website-Pflege",
    "Website-Redesign",
    "Landing Page",
    "SEO-Optimierung",
    "Performance-Optimierung",
    "Content-Pflege",
    # ── Infrastruktur / Security ──
    "Server-Administration",
    "Server-Einrichtung",
    "Hosting-Migration",
    "Backup-Einrichtung",
    "Monitoring-Einrichtung",
    "Security-Audit",
    "Security-Härtung",
    "Penetrationstest",
    "Update / Patching",
    "Incident-Response",
    # ── Beratung / Kommunikation ──
    "Beratung",
    "IT-Beratung",
    "Datenschutz-Beratung",
    "DSGVO-Dokumentation",
    "Anforderungsanalyse",
    "Konzeption",
    "Angebotserstellung",
    "Kundentermin",
    "Telefonat",
    "E-Mail-Kommunikation",
    "Projektmanagement",
    "Dokumentation",
    "Schulung / Einweisung",
    "Support",
    "Wartung",
    "Recherche",
]

TAXONOMIES: dict[str, list[str]] = {
    "role": list(dict.fromkeys(_ROLE)),
    "source": list(dict.fromkeys(_SOURCE)),
    "tag": _TAG,
    "branche": list(dict.fromkeys(_BRANCHE)),
    "zielsystem": list(dict.fromkeys(_ZIELSYSTEM)),
    "vendor": list(dict.fromkeys(_VENDOR)),
    "taetigkeit": list(dict.fromkeys(_TAETIGKEIT)),
}

# Synonym → kanonische Schreibweise (Keys werden gefoldet verglichen).
SYNONYMS: dict[str, str] = {
    # Rollen
    "gf": "Geschäftsführung",
    "geschaftsfuhrer": "Geschäftsführung",
    "geschaftsfuhrerin": "Geschäftsführung",
    "geschaftsfuhrung": "Geschäftsführung",
    "ceo": "Geschäftsführung",
    "managing director": "Geschäftsführung",
    "owner": "Inhaber/in",
    "inhaber": "Inhaber/in",
    "inhaberin": "Inhaber/in",
    "dsb": "Datenschutzbeauftragte/r",
    "datenschutzbeauftragter": "Datenschutzbeauftragte/r",
    "it leiter": "IT-Leitung",
    "it-leiter": "IT-Leitung",
    "head of it": "IT-Leitung",
    # Quellen
    "linked in": "LinkedIn",
    "osm": "OpenStreetMap",
    "ki recherche": "KI-Recherche",
    "kaltakquise": "Kaltakquise Telefon",
    "empfehlungen": "Empfehlung",
    # Tags / Branchen
    "dsvgo": "DSGVO",
    "dsgvo": "DSGVO",
    "hausverwaltungen": "Hausverwaltung",
    "steuerberaterin": "Steuerberater",
    "steuerkanzlei": "Steuerberater",
    "makler": "Immobilienmakler",
    "onlineshop": "E-Commerce / Onlineshop",
    "e-commerce": "E-Commerce / Onlineshop",
    "webshop": "Webshop",
    "agentur": "Agentur / IT-Dienstleister",
    # Zielsysteme
    "datev online": "DATEV Unternehmen online",
    "business central": "Microsoft Dynamics NAV / Business Central",
    "dynamics": "Microsoft Dynamics 365",
    "office 365": "Microsoft 365",
    "o365": "Microsoft 365",
    "m365": "Microsoft 365",
    # Vendors
    "1blu": "IONOS",
    "google": "Google Workspace",
    "msft": "Microsoft 365",
    "telefonica": "o2 / Telefónica",
}


# --------------------------------------------------------------------------- #
#  Normalisierung (rein)
# --------------------------------------------------------------------------- #
def fold(s: str) -> str:
    """Vergleichs-Schlüssel: trim, lowercase, Diakritika weg (ä→a, é→e)."""
    nfkd = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_SYNONYMS_FOLDED = {fold(k): v for k, v in SYNONYMS.items()}
_CANONICAL_BY_FOLD: dict[str, dict[str, str]] = {
    field: {fold(v): v for v in values} for field, values in TAXONOMIES.items()
}


def canonicalize(field: str, value: str) -> str:
    """Kanonische Schreibweise: Synonym-Treffer → kanonisch; sonst Case-Variante
    eines kuratierten Werts → kuratierte Schreibweise; sonst Original (getrimmt).
    Creatable: unbekannte Werte bleiben unangetastet erlaubt."""
    v = (value or "").strip()
    if not v:
        return v
    key = fold(v)
    if key in _SYNONYMS_FOLDED:
        return _SYNONYMS_FOLDED[key]
    return _CANONICAL_BY_FOLD.get(field, {}).get(key, v)


def merge_suggestions(field: str, own_counts: dict[str, int],
                      q: str = "", limit: int = 50) -> list[str]:
    """Kuratierte Liste ∪ eigene Bestandswerte, fold-dedupliziert (kuratierte
    Schreibweise gewinnt). Ranking: eigene Häufigkeit desc → alphabetisch.
    Optionaler Substring-Filter q (gefoldet)."""
    counts_folded: dict[str, int] = {}
    for raw, n in own_counts.items():
        canon = canonicalize(field, raw)
        counts_folded[fold(canon)] = counts_folded.get(fold(canon), 0) + n

    merged: dict[str, str] = {}          # fold-key → Anzeige-Schreibweise
    for v in TAXONOMIES.get(field, []):
        merged.setdefault(fold(v), v)
    for raw in own_counts:
        canon = canonicalize(field, raw)
        merged.setdefault(fold(canon), canon)

    items = list(merged.items())
    if q:
        qf = fold(q)
        items = [(k, v) for k, v in items if qf in k]
    items.sort(key=lambda kv: (-counts_folded.get(kv[0], 0), kv[1].lower()))
    return [v for _, v in items[:limit]]
