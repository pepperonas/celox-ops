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

**Domains sind nicht eindeutig zuordenbar.** Ein Abo heißt nur „.DE Domain"; das
Domain-Detail enthält keine `subscription_id`, und mehrere Domains teilen Preis
und Ablaufdatum. Statt zu raten trägt die Ausgabe den generischen Namen und in
den Notizen die Liste der Domains dieser TLD aus dem Portfolio. Der **VPS** ist
dagegen exakt zuordenbar: die VPS-Liste nennt ihre `subscription_id`.

Die Abbildung ist rein und damit netz-/DB-frei testbar; nur `fetch_*` spricht HTTP.
"""
import re
from calendar import monthrange
from datetime import date, datetime
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


def describe(sub: dict, vps_by_subscription: dict[str, dict] | None = None) -> str:
    """Beschreibung der Ausgabe. Rein.

    Der VPS bekommt Plan und Hostname, weil die VPS-Liste ihre `subscription_id`
    nennt — das ist eine belegte Zuordnung. Domains bleiben generisch, weil die
    API nicht sagt, welche Domain zu welchem Abo gehört.
    """
    name = (sub.get("name") or "Abo").strip()
    vps = (vps_by_subscription or {}).get(sub.get("id"))
    if vps:
        host = (vps.get("hostname") or "").strip()
        plan = (vps.get("plan") or name).strip()
        return f"VPS {plan}{f' · {host}' if host else ''} ({VENDOR})"
    tld = tld_of(name)
    if tld:
        return f"Domain {tld} ({VENDOR})"
    return f"{name} ({VENDOR})"


def build_notes(sub: dict, *, domains_by_tld: dict[str, list[str]] | None = None,
                vps_by_subscription: dict[str, dict] | None = None) -> str:
    """Notiz mit Abo-ID, Verlängerungstermin, Periode — und bei Domains der
    Portfolio-Liste dieser TLD, damit man selbst zuordnen kann. Rein.
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
        domains = (domains_by_tld or {}).get(tld) or []
        if domains:
            shown = ", ".join(domains[:12])
            more = f" … ({len(domains)} insgesamt)" if len(domains) > 12 else ""
            lines.append(f"{tld}-Domains im Konto: {shown}{more}")
            lines.append("Die API sagt nicht, welche Domain zu diesem Abo gehört.")
    return "\n".join(lines)


def external_ref(sub: dict, billed_on: date) -> str:
    """Herkunftsschlüssel: Abo + Abrechnungszeitraum. Rein.

    Enthält das Datum, damit die Verlängerung im nächsten Jahr als **neue**
    Ausgabe importiert werden kann — derselbe Zeitraum aber nie zweimal.
    """
    return f"{REF_PREFIX}:{sub.get('id') or 'unbekannt'}:{billed_on.isoformat()}"


def to_expense(sub: dict, *, today: date,
               domains_by_tld: dict[str, list[str]] | None = None,
               vps_by_subscription: dict[str, dict] | None = None) -> dict | None:
    """Abo → Ausgaben-Entwurf, oder None wenn es keinen belegten Betrag/Termin gibt.
    Rein."""
    amount = parse_price_cents(sub.get("renewal_price") if sub.get("renewal_price") is not None
                               else sub.get("total_price"))
    billed_on = last_billed_on(sub, today)
    if amount is None or amount <= 0 or billed_on is None:
        return None
    return {
        "description": describe(sub, vps_by_subscription)[:500],
        "category": category_for(sub.get("name") or "").value,
        "amount": str(amount),
        "date": billed_on.isoformat(),
        "vendor": VENDOR,
        "recurring": True,
        "notes": build_notes(sub, domains_by_tld=domains_by_tld,
                             vps_by_subscription=vps_by_subscription),
        "external_ref": external_ref(sub, billed_on),
        "currency": (sub.get("currency_code") or "EUR").upper(),
        "subscription_id": sub.get("id"),
        "status": sub.get("status"),
    }


def build_drafts(subscriptions: list[dict], *, today: date,
                 domains: list[dict] | None = None,
                 vps: list[dict] | None = None) -> dict:
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
                           vps_by_subscription=vps_by_subscription)
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


async def load_drafts(key: str, *, today: date | None = None) -> dict:
    """Kompletter Lauf: abrufen und in Entwürfe übersetzen."""
    from app.services.business_time import today as business_today

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        account = await fetch_account(key, client)
    result = build_drafts(account["subscriptions"], today=today or business_today(),
                          domains=account["domains"], vps=account["vps"])
    result["counts"] = {
        "subscriptions": len(account["subscriptions"]),
        "domains": len(account["domains"]),
        "vps": len(account["vps"]),
    }
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
    "HostingerError", "VENDOR", "build_drafts", "category_for", "describe",
    "external_ref", "fetch_account", "last_billed_on", "load_drafts",
    "parse_price_cents", "period_label", "shift_back", "tld_of", "to_expense",
    "total_of", "build_notes",
]
