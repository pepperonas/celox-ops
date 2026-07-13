"""Zentrale Duplikat-Erkennung für Rainmaker-Leads.

Auto-Skip-Hierarchie: **E-Mail** (normalisiert) → **Website/Profil-URL**
(normalisiert) → **exakter Ansprechpartner-Name**. Der **Firmenname ist
bewusst KEIN Auto-Key** — verschiedene Personen teilen sich denselben
Arbeitgeber (im Bestand z. B. 22 eigenständige Leads „Selbstständig"); er
dient nur der **Fuzzy-Warnung** (`norm_company`).

Die Normalisierungen `norm_email`/`norm_website` MÜSSEN mit den generierten
SQL-Spalten `email_norm`/`website_norm` in `models/rainmaker_lead.py`
übereinstimmen (dieselben Regeln → die partiellen Unique-Indizes greifen exakt
dort, wo der App-Code ein Duplikat sieht). Reine Bausteine, netzfrei testbar.
"""
import re

# Match-Gründe für den Import-Report (welches Feld hat gematcht).
MATCH_EMAIL = "email"
MATCH_WEBSITE = "website"
MATCH_NAME = "name"

# Rechtsformen/Firmierungs-Zusätze, die für den Fuzzy-Vergleich wegfallen.
_LEGAL_FORMS = {
    "gmbh", "mbh", "ug", "ag", "kg", "kgaa", "ohg", "gbr", "gmbhcokg",
    "se", "eg", "ev", "ek", "partg", "partgmbb", "haftungsbeschränkt",
    "haftungsbeschraenkt", "co", "cokg", "inc", "ltd", "llc", "plc",
    "corp", "corporation", "company", "und", "and",
}


def norm_email(email: str | None) -> str | None:
    """lowercase + getrimmt; leer → None. Spiegelt SQL `nullif(lower(btrim(email)),'')`."""
    v = (email or "").strip().lower()
    return v or None


def norm_website(url: str | None) -> str | None:
    """Schema + führendes www. + Trailing-Slashes entfernen, lowercase. **Pfad
    bleibt erhalten** (sonst kollabieren alle LinkedIn-Profile auf linkedin.com).
    Spiegelt die SQL-`website_norm`-Generierung exakt."""
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.rstrip("/").strip()
    return u or None


def norm_name(name: str | None) -> str | None:
    """Exakter Personen-/Ansprechpartner-Name: lowercase, Whitespace kollabiert."""
    v = re.sub(r"\s+", " ", (name or "").strip().lower())
    return v or None


def norm_company(name: str | None) -> str | None:
    """Firmenname für den Fuzzy-Vergleich: lowercase, Rechtsformen (GmbH/AG/e.K.…)
    und Interpunktion entfernt, Tokens sortiert-neutralisiert. Nur für Warnungen —
    NIE als Auto-Skip-Schlüssel (würde eigenständige Leads verschmelzen)."""
    v = (name or "").lower().replace("&", " ")
    v = re.sub(r"[^a-z0-9äöüß]+", " ", v)          # Interpunktion → Space (e.k. → e k)
    toks = [t for t in v.split() if t and t not in _LEGAL_FORMS and len(t) > 1]
    return " ".join(toks) or None


class DedupIndex:
    """Sammelt die normalisierten Schlüssel bestehender + im laufenden Batch
    angelegter Leads. `match()` liefert `(lead|None, reason)`; nach jedem Insert
    `add()` aufrufen, damit Batch-interne Duplikate ebenfalls greifen.

    Der `lead`-Wert ist opak (ORM-Objekt oder ein Platzhalter in der Preview) —
    der Index kümmert sich nur um die Schlüssel."""

    def __init__(self) -> None:
        self._by_email: dict[str, object] = {}
        self._by_website: dict[str, object] = {}
        self._by_name: dict[str, object] = {}

    def add(self, lead: object, *, email: str | None = None,
            website: str | None = None, name: str | None = None) -> None:
        if e := norm_email(email):
            self._by_email.setdefault(e, lead)
        if w := norm_website(website):
            self._by_website.setdefault(w, lead)
        if n := norm_name(name):
            self._by_name.setdefault(n, lead)

    def match(self, *, email: str | None = None, website: str | None = None,
              name: str | None = None) -> tuple[object | None, str | None]:
        """Erster Treffer nach Priorität E-Mail → Website → Name."""
        if (e := norm_email(email)) and e in self._by_email:
            return self._by_email[e], MATCH_EMAIL
        if (w := norm_website(website)) and w in self._by_website:
            return self._by_website[w], MATCH_WEBSITE
        if (n := norm_name(name)) and n in self._by_name:
            return self._by_name[n], MATCH_NAME
        return None, None
