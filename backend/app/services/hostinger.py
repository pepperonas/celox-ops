"""Laufende Hostinger-Kosten (VPS, Domains) als Ausgaben übernehmen.

**Was die API hergibt — und was nicht.** `GET /api/billing/v1/subscriptions`
liefert **Verträge**, keine Zahlungsbelege: Startdatum, Preis, Abrechnungsperiode
und den nächsten Abrechnungstermin. Ein Rechnungs-Endpunkt existiert nicht
(`/api/billing/v1/orders` ist POST-only, also zum *Bestellen*). Deshalb überträgt
dieser Import den **Ist-Stand**: je aktivem Abo eine wiederkehrende Ausgabe,
datiert auf die letzte Abrechnung. Vergangene Jahre werden bewusst NICHT
hochgerechnet — das wären abgeleitete Buchungen, die die API nirgends bestätigt.

**Preise kommen in Cent.** `total_price: 1199` heißt 11,99 €. Ohne Division wäre
jede Ausgabe hundertfach zu hoch — am echten Konto geprüft, nicht aus der Doku
geraten.

**Welche Domain gehört zu welchem Abo?** Die API sagt es nicht direkt: ein Abo
heißt nur „.DE Domain", das Domain-Detail trägt keine `subscription_id`, und kein
Feld der einen Seite enthält einen Wert der anderen (beide Richtungen geprüft).
Am echten Konto gemessen gibt es aber einen belastbaren Verbund: **je TLD stimmt
die Anzahl exakt** (.de 28/28, .com 3/3, .wtf 4/4, .camp/.io/.xyz 1/1), und die
Domain wird unmittelbar nach dem Abo registriert — bei 34 von 38 innerhalb von
**1–60 Sekunden**. `match_domains` nutzt das: innerhalb einer TLD werden beide
Seiten nach Anlagezeit sortiert und **in dieser Reihenfolge** gepaart. Das ist bei
gleicher Anzahl die einzige reihenfolgetreue Zuordnung und deckt sich in jeder
Gruppe mit der kostenminimalen (per Hungarian-Verfahren gegengerechnet).

Es bleibt eine **Ableitung, keine API-Auskunft** — deshalb nennt jede Notiz den
Zeitabstand, große Abstände werden als prüfbedürftig markiert, und eine
Korrektur des Nutzers (`hostinger_domain_links`) schlägt die Ableitung immer.
Der **VPS** braucht das alles nicht: die VPS-Liste nennt ihre `subscription_id`.

Die Abbildung ist rein und damit netz-/DB-frei testbar; nur `fetch_*` spricht HTTP.
"""
import re
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from app.models.expense import ExpenseCategory

API_BASE = "https://developers.hostinger.com"
VENDOR = "Hostinger"
TIMEOUT = 20.0
# Der Herkunftsschlüssel steht in expenses.external_ref und macht den Import
# idempotent (siehe partieller Unique-Index am Modell).
REF_PREFIX = "hostinger"

# Abo-Namen → Ausgabenkategorie. Alles Domainartige ist `domain`, Server und
# Webhosting `hosting`; Unbekanntes landet in `sonstige` statt in einer geratenen
# Kategorie.
_HOSTING_HINTS = ("kvm", "vps", "cloud", "hosting", "server", "business", "premium")


def parse_price_cents(value) -> Decimal | None:
    """Cent-Betrag der API → Euro als Decimal. Rein.

    `None` bei Unbrauchbarem — eine Ausgabe ohne belegten Betrag wird nicht
    angelegt, sondern gemeldet.
    """
    if isinstance(value, bool) or value is None:
        return None
    try:
        cents = int(value)
    except (TypeError, ValueError):
        return None
    if cents < 0:
        return None
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def tld_of(name: str) -> str | None:
    """„.DE Domain" → „.de". Rein; None wenn es kein Domain-Abo ist."""
    match = re.match(r"^\s*(\.[A-Za-z0-9-]+)\s+Domain\s*$", name or "", re.IGNORECASE)
    return match.group(1).lower() if match else None


def domain_tld(domain: str) -> str | None:
    """„mapsmate.de" → „.de". Rein."""
    name = (domain or "").strip().lower().rstrip(".")
    return "." + name.split(".", 1)[1] if "." in name else None


# Bis zu diesem Abstand zwischen Abo-Anlage und Domain-Registrierung gehören
# beide sichtbar zur selben Bestellung (gemessen: 34 von 38 unter 60 s). Darüber
# stimmt die Reihenfolge weiterhin, aber die Zuordnung wird als prüfbedürftig
# markiert statt stillschweigend behauptet.
SAME_ORDER_SECONDS = 300


def match_domains(subscriptions: list[dict], domains: list[dict]) -> dict[str, dict]:
    """Domain-Abo → Domain, abgeleitet aus der Bestellreihenfolge. Rein.

    Vorgehen je TLD: beide Seiten nach Anlagezeit sortieren und reihenfolgetreu
    paaren. Bei gleicher Anzahl ist das die einzig mögliche monotone Zuordnung.
    Stimmen die Anzahlen **nicht** (eine Domain wurde weggezogen oder extern
    dazugekauft), richtet ein kleiner Ausrichtungs-Durchlauf die Folgen
    aneinander aus und lässt die überzähligen Einträge bewusst **unzugeordnet** —
    ein Abo ohne belegbare Domain bleibt lieber generisch.

    Rückgabe je `subscription_id`: `domain`, `delta_seconds` (Abstand der
    Anlagezeiten, None wenn eine Seite kein Datum hat), `confidence`
    (`same_order` | `sequence`) und `candidates` (alle Domains dieser TLD, für
    die Korrektur in der Oberfläche).
    """
    by_tld_subs: dict[str, list[dict]] = {}
    by_tld_doms: dict[str, list[dict]] = {}
    for sub in subscriptions or []:
        if not isinstance(sub, dict):
            continue
        tld = tld_of(sub.get("name") or "")
        if tld:
            by_tld_subs.setdefault(tld, []).append(sub)
    for entry in domains or []:
        if not isinstance(entry, dict):
            continue
        tld = domain_tld(entry.get("domain") or "")
        if tld:
            by_tld_doms.setdefault(tld, []).append(entry)

    def key(item, field):
        parsed = _parse_dt(item.get(field))
        # Ohne Datum ans Ende, damit datierte Einträge die Reihenfolge bestimmen.
        return (parsed is None, parsed or datetime.max.replace(tzinfo=UTC))

    out: dict[str, dict] = {}
    for tld, subs in by_tld_subs.items():
        doms = sorted(by_tld_doms.get(tld, []), key=lambda d: key(d, "created_at"))
        subs = sorted(subs, key=lambda s: key(s, "created_at"))
        candidates = [(d.get("domain") or "").strip().lower() for d in doms]
        pairs = _align(subs, doms)
        for sub, dom in pairs:
            a, b = _parse_dt(sub.get("created_at")), _parse_dt(dom.get("created_at"))
            if not a or not b:
                # Ohne Zeitstempel auf beiden Seiten gibt es keinen Beleg für die
                # Paarung — dann wird keine Domain behauptet.
                continue
            delta = int(abs((b - a).total_seconds()))
            out[sub.get("id")] = {
                "domain": (dom.get("domain") or "").strip().lower(),
                "delta_seconds": delta,
                "confidence": ("same_order" if delta <= SAME_ORDER_SECONDS else "sequence"),
                "candidates": candidates,
            }
        # Abos ohne belegbaren Partner: generisch, aber mit den Kandidaten, damit
        # der Nutzer im Dialog selbst zuordnen kann.
        for sub in subs:
            if sub.get("id") not in out:
                out[sub.get("id")] = {"domain": None, "delta_seconds": None,
                                      "confidence": "unmatched", "candidates": candidates}
    return out


def _align(subs: list[dict], doms: list[dict]) -> list[tuple[dict, dict]]:
    """Reihenfolgetreue Paarung zweier sortierter Folgen mit minimalem
    Gesamtabstand; überzählige Einträge bleiben ungepaart. Rein.

    Bei gleicher Länge ist das Ergebnis die positionsweise Paarung — genau die
    Regel, die am Konto gegen das kostenminimale Verfahren geprüft wurde. Der
    Ausrichtungs-Durchlauf existiert nur für den Fall ungleicher Anzahlen.
    """
    n, m = len(subs), len(doms)
    if n == 0 or m == 0:
        return []
    if n == m:
        return list(zip(subs, doms, strict=True))

    def cost(i: int, j: int) -> float:
        a, b = _parse_dt(subs[i].get("created_at")), _parse_dt(doms[j].get("created_at"))
        if not a or not b:
            return float(SAME_ORDER_SECONDS * 10)
        return abs((b - a).total_seconds())

    # Überzählige Einträge auslassen kostet mehr als jede plausible Paarung, damit
    # nur bei echtem Überhang übersprungen wird.
    skip = 400_000.0
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        best[i][0] = best[i - 1][0] + skip
    for j in range(1, m + 1):
        best[0][j] = best[0][j - 1] + skip
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best[i][j] = min(best[i - 1][j - 1] + cost(i - 1, j - 1),
                             best[i - 1][j] + skip, best[i][j - 1] + skip)
    pairs: list[tuple[dict, dict]] = []
    i, j = n, m
    while i > 0 and j > 0:
        if best[i][j] == best[i - 1][j - 1] + cost(i - 1, j - 1):
            pairs.append((subs[i - 1], doms[j - 1]))
            i, j = i - 1, j - 1
        elif best[i][j] == best[i - 1][j] + skip:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


def category_for(name: str) -> ExpenseCategory:
    """Abo-Name → Kategorie. Rein."""
    if tld_of(name):
        return ExpenseCategory.domain
    low = (name or "").lower()
    if any(hint in low for hint in _HOSTING_HINTS):
        return ExpenseCategory.hosting
    return ExpenseCategory.sonstige


def _parse_dt(value) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def shift_back(day: date, count: int, unit: str) -> date:
    """`day` um `count` Perioden zurück. Rein.

    Monatsende wird geklemmt: der 31.03. minus einen Monat ist der 28./29.02.,
    nicht ein ungültiges Datum.
    """
    count = max(1, int(count or 1))
    unit = (unit or "month").lower().rstrip("s")
    if unit == "day":
        from datetime import timedelta
        return day - timedelta(days=count)
    if unit == "week":
        from datetime import timedelta
        return day - timedelta(weeks=count)
    months = count * 12 if unit == "year" else count
    total = (day.year * 12 + (day.month - 1)) - months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def last_billed_on(sub: dict, today: date) -> date | None:
    """Datum der letzten Abrechnung. Rein.

    Ausgangspunkt ist `next_billing_at` minus eine Periode. Liegt dieser Termin
    noch in der Zukunft, wurde er noch nicht abgerechnet — dann geht es eine
    weitere Periode zurück. (Realer Fall im Konto: Registrierung 2025-08-29,
    nächste Abrechnung 2027-07-31 — Hostinger richtet Verlängerungstermine
    teilweise aus, der Abstand ist dann größer als eine Periode.)

    Vor dem Vertragsbeginn wurde nichts abgerechnet, also gilt mindestens
    `created_at`. Und nie ein Datum in der Zukunft — eine Ausgabe, die noch nicht
    geflossen ist, gehört nicht in die EÜR.
    """
    created = _parse_dt(sub.get("created_at"))
    created_day = created.date() if created else None
    nxt = _parse_dt(sub.get("next_billing_at"))
    count = sub.get("billing_period") or 1
    unit = sub.get("billing_period_unit") or "month"

    if nxt:
        candidate = shift_back(nxt.date(), count, unit)
        # Zurück, bis der Termin in der Vergangenheit liegt. Die Schleife ist
        # gedeckelt, damit kaputte Daten sie nicht endlos laufen lassen.
        for _ in range(40):
            if candidate <= today:
                break
            candidate = shift_back(candidate, count, unit)
    elif created_day:
        candidate = created_day
    else:
        return None

    if created_day:
        candidate = max(candidate, created_day)
    return min(candidate, today)


def period_label(sub: dict) -> str:
    count = max(1, int(sub.get("billing_period") or 1))
    unit = (sub.get("billing_period_unit") or "month").lower().rstrip("s")
    words = {"year": ("Jahr", "Jahre"), "month": ("Monat", "Monate"),
             "week": ("Woche", "Wochen"), "day": ("Tag", "Tage")}
    single, plural = words.get(unit, (unit, unit))
    return f"{count} {single if count == 1 else plural}"


def describe(sub: dict, vps_by_subscription: dict[str, dict] | None = None,
             domain: str | None = None) -> str:
    """Beschreibung der Ausgabe. Rein.

    Der VPS bekommt Plan und Hostname (belegt über die `subscription_id`), eine
    Domain ihren Namen — steht keiner fest, bleibt es beim generischen „.de".
    """
    name = (sub.get("name") or "Abo").strip()
    vps = (vps_by_subscription or {}).get(sub.get("id"))
    if vps:
        host = (vps.get("hostname") or "").strip()
        plan = (vps.get("plan") or name).strip()
        return f"VPS {plan}{f' · {host}' if host else ''} ({VENDOR})"
    tld = tld_of(name)
    if tld:
        return f"Domain {domain or tld} ({VENDOR})"
    return f"{name} ({VENDOR})"


def build_notes(sub: dict, *, domains_by_tld: dict[str, list[str]] | None = None,
                vps_by_subscription: dict[str, dict] | None = None,
                match: dict | None = None, confirmed: bool = False) -> str:
    """Notiz mit Abo-ID, Verlängerungstermin, Periode — und bei Domains, **woher**
    der Domainname kommt. Rein.

    Die Herkunft steht bewusst in der Buchung: eine bestätigte Zuordnung, eine
    Ableitung aus derselben Bestellung (Sekundenabstand) oder eine Ableitung nur
    aus der Reihenfolge (großer Abstand → prüfen). Ohne diesen Satz sähe ein
    abgeleiteter Name später wie eine Auskunft der API aus.
    """
    lines = [f"Abo {sub.get('id') or '?'} · Periode {period_label(sub)}"]
    nxt = _parse_dt(sub.get("next_billing_at"))
    if nxt:
        lines.append(f"Nächste Verlängerung: {nxt.date().isoformat()}")
    elif sub.get("status") == "non_renewing":
        exp = _parse_dt(sub.get("expires_at"))
        lines.append("Wird nicht verlängert"
                     + (f", läuft aus am {exp.date().isoformat()}" if exp else ""))
    vps = (vps_by_subscription or {}).get(sub.get("id"))
    if vps:
        ips = ", ".join(a.get("address", "") for a in (vps.get("ipv4") or []) if a.get("address"))
        lines.append(f"VPS {vps.get('plan') or ''} · {vps.get('hostname') or ''}"
                     + (f" · {ips}" if ips else ""))
    tld = tld_of(sub.get("name") or "")
    if tld:
        match = match or {}
        domain = match.get("domain")
        delta = match.get("delta_seconds")
        if confirmed and domain:
            lines.append(f"Domain {domain} — Zuordnung bestätigt.")
        elif domain and match.get("confidence") == "same_order":
            lines.append(f"Domain {domain} — abgeleitet: {_ago(delta)} nach dem Abo "
                         f"registriert, also dieselbe Bestellung.")
        elif domain:
            lines.append(f"Domain {domain} — abgeleitet aus der Bestellreihenfolge"
                         + (f", registriert {_ago(delta)} nach dem Abo" if delta else "")
                         + ". Bitte prüfen.")
        else:
            domains = (domains_by_tld or {}).get(tld) or []
            if domains:
                shown = ", ".join(domains[:12])
                more = f" … ({len(domains)} insgesamt)" if len(domains) > 12 else ""
                lines.append(f"Keine Domain zuordenbar. {tld}-Domains im Konto: {shown}{more}")
        if domain and not confirmed:
            lines.append("Die API verknüpft Abo und Domain nicht — Zuordnung über die "
                         "Anlagezeit, in der Oberfläche korrigierbar.")
    return "\n".join(lines)


def _ago(seconds: int | None) -> str:
    """Sekunden als lesbare Dauer. Rein."""
    if seconds is None:
        return "unbekannte Zeit"
    if seconds < 90:
        return f"{seconds} s"
    if seconds < 5400:
        return f"{round(seconds / 60)} min"
    if seconds < 172800:
        return f"{round(seconds / 3600)} h"
    return f"{round(seconds / 86400)} Tage"


def external_ref(sub: dict, billed_on: date) -> str:
    """Herkunftsschlüssel: Abo + Abrechnungszeitraum. Rein.

    Enthält das Datum, damit die Verlängerung im nächsten Jahr als **neue**
    Ausgabe importiert werden kann — derselbe Zeitraum aber nie zweimal.
    """
    return f"{REF_PREFIX}:{sub.get('id') or 'unbekannt'}:{billed_on.isoformat()}"


def to_expense(sub: dict, *, today: date,
               domains_by_tld: dict[str, list[str]] | None = None,
               vps_by_subscription: dict[str, dict] | None = None,
               match: dict | None = None, confirmed_domain: str | None = None) -> dict | None:
    """Abo → Ausgaben-Entwurf, oder None wenn es keinen belegten Betrag/Termin gibt.
    Rein.

    `confirmed_domain` ist eine früher bestätigte Korrektur des Nutzers und
    schlägt die abgeleitete Zuordnung.
    """
    amount = parse_price_cents(sub.get("renewal_price") if sub.get("renewal_price") is not None
                               else sub.get("total_price"))
    billed_on = last_billed_on(sub, today)
    if amount is None or amount <= 0 or billed_on is None:
        return None
    match = dict(match or {})
    domain = confirmed_domain or match.get("domain")
    return {
        "description": describe(sub, vps_by_subscription, domain=domain)[:500],
        "category": category_for(sub.get("name") or "").value,
        "amount": str(amount),
        "date": billed_on.isoformat(),
        "vendor": VENDOR,
        "recurring": True,
        "notes": build_notes(sub, domains_by_tld=domains_by_tld,
                             vps_by_subscription=vps_by_subscription,
                             match={**match, "domain": domain},
                             confirmed=bool(confirmed_domain)),
        "external_ref": external_ref(sub, billed_on),
        "currency": (sub.get("currency_code") or "EUR").upper(),
        "subscription_id": sub.get("id"),
        "status": sub.get("status"),
        # Für die Oberfläche: Zuordnung sichtbar machen und korrigierbar halten.
        "domain": domain,
        "domain_confidence": ("confirmed" if confirmed_domain
                              else match.get("confidence") or "unmatched"),
        "domain_delta_seconds": match.get("delta_seconds"),
        "domain_candidates": match.get("candidates") or [],
    }


def build_drafts(subscriptions: list[dict], *, today: date,
                 domains: list[dict] | None = None,
                 vps: list[dict] | None = None,
                 confirmed: dict[str, str] | None = None) -> dict:
    """Alle Abos → Entwürfe + Bericht, was übersprungen wurde. Rein.

    Nur `active`-Abos werden übernommen (der Ist-Stand der laufenden Kosten).
    Nicht verlängernde und unbrauchbare Einträge werden **gezählt und benannt** —
    stilles Weglassen wäre der schlimmere Fehler.
    """
    domains_by_tld: dict[str, list[str]] = {}
    for entry in domains or []:
        name = (entry.get("domain") or "").strip().lower()
        if "." in name:
            domains_by_tld.setdefault("." + name.rsplit(".", 1)[1], []).append(name)
    for names in domains_by_tld.values():
        names.sort()

    vps_by_subscription = {v.get("subscription_id"): v for v in (vps or [])
                           if v.get("subscription_id")}
    # Die Zuordnung braucht ALLE Domain-Abos, auch die nicht übernommenen — sonst
    # verschiebt sich die Reihenfolge und jede Domain landet beim falschen Abo.
    matches = match_domains(subscriptions or [], domains or [])
    confirmed = confirmed or {}

    drafts: list[dict] = []
    skipped: list[str] = []
    for sub in subscriptions or []:
        if not isinstance(sub, dict):
            continue
        label = f"{sub.get('name') or 'Abo'} ({sub.get('id') or '?'})"
        if (sub.get("status") or "").lower() != "active":
            skipped.append(f"{label}: Status '{sub.get('status')}' — nicht in den laufenden Kosten")
            continue
        draft = to_expense(sub, today=today, domains_by_tld=domains_by_tld,
                           vps_by_subscription=vps_by_subscription,
                           match=matches.get(sub.get("id")),
                           confirmed_domain=confirmed.get(sub.get("id")))
        if draft is None:
            skipped.append(f"{label}: kein belegter Betrag oder Abrechnungstermin")
            continue
        if draft["currency"] != "EUR":
            skipped.append(f"{label}: Währung {draft['currency']} — nur EUR wird übernommen")
            continue
        drafts.append(draft)

    drafts.sort(key=lambda d: (d["date"], d["description"]), reverse=True)
    return {"drafts": drafts, "skipped": skipped}


# --------------------------------------------------------------------------- #
#  HTTP (die einzigen unreinen Teile)
# --------------------------------------------------------------------------- #
class HostingerError(Exception):
    """Fehler beim Abruf — trägt eine Klartextmeldung für die Oberfläche."""


async def _get(client: httpx.AsyncClient, key: str, path: str) -> list | dict:
    try:
        resp = await client.get(f"{API_BASE}{path}",
                                headers={"Authorization": f"Bearer {key}",
                                         "Accept": "application/json"})
    except httpx.HTTPError as exc:
        raise HostingerError(f"Hostinger nicht erreichbar ({type(exc).__name__}).") from exc
    if resp.status_code in (401, 403):
        raise HostingerError(
            "Hostinger lehnt den API-Key ab (401/403). Key in den Einstellungen prüfen — "
            "erzeugt wird er im hPanel unter Konto → API.")
    if resp.status_code == 429:
        raise HostingerError("Hostinger drosselt die Anfragen (429) — später erneut versuchen.")
    if resp.status_code >= 400:
        raise HostingerError(f"Hostinger antwortete mit HTTP {resp.status_code} auf {path}.")
    try:
        return resp.json()
    except ValueError as exc:
        raise HostingerError(f"Unlesbare Antwort von {path}.") from exc


async def fetch_account(key: str, client: httpx.AsyncClient) -> dict:
    """Abos + Domain-Portfolio + VPS-Liste holen.

    Nur die Abos sind Pflicht; Portfolio und VPS-Liste dienen der Anreicherung
    und dürfen ausfallen, ohne den Import zu verhindern.
    """
    subscriptions = await _get(client, key, "/api/billing/v1/subscriptions")
    if not isinstance(subscriptions, list):
        raise HostingerError("Unerwartete Antwort auf die Abo-Liste.")

    domains: list = []
    vps: list = []
    for path, target in (("/api/domains/v1/portfolio", "domains"),
                         ("/api/vps/v1/virtual-machines", "vps")):
        try:
            data = await _get(client, key, path)
        except HostingerError:
            continue          # Anreicherung ist optional
        if isinstance(data, list):
            if target == "domains":
                domains = data
            else:
                vps = data
    return {"subscriptions": subscriptions, "domains": domains, "vps": vps}


async def load_drafts(key: str, *, today: date | None = None,
                      confirmed: dict[str, str] | None = None) -> dict:
    """Kompletter Lauf: abrufen und in Entwürfe übersetzen."""
    from app.services.business_time import today as business_today

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        account = await fetch_account(key, client)
    result = build_drafts(account["subscriptions"], today=today or business_today(),
                          domains=account["domains"], vps=account["vps"],
                          confirmed=confirmed)
    result["counts"] = {
        "subscriptions": len(account["subscriptions"]),
        "domains": len(account["domains"]),
        "vps": len(account["vps"]),
    }
    # Alle Domains des Kontos: die Oberfläche braucht sie, um eine Zuordnung
    # korrigieren zu können.
    result["all_domains"] = sorted(
        (e.get("domain") or "").strip().lower() for e in account["domains"]
        if (e.get("domain") or "").strip())
    # Rohdaten mitgeben, damit der Aufrufer nach einer Korrektur neu aufbauen kann
    # OHNE ein zweites Mal abzurufen.
    result["account"] = account
    return result


def total_of(drafts: list[dict]) -> Decimal:
    """Summe der Entwürfe (für die Anzeige). Rein."""
    total = Decimal("0")
    for d in drafts:
        try:
            total += Decimal(str(d.get("amount") or "0"))
        except Exception:  # noqa: BLE001
            continue
    return total.quantize(Decimal("0.01"))


__all__ = [
    "SAME_ORDER_SECONDS", "HostingerError", "VENDOR", "build_drafts", "build_notes",
    "category_for", "describe", "domain_tld", "external_ref", "fetch_account",
    "last_billed_on", "load_drafts", "match_domains", "parse_price_cents",
    "period_label", "shift_back", "tld_of", "to_expense", "total_of",
]
