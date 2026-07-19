"""Customer-Handoff an portal.celox.io / datenschutz.celox.io (Absenderseite).

Verbindliche Quelle: /Users/martin/claude/_integration/customer-handoff-contract.md
— Envelope (§3), Feld-Whitelists (§4.1/§5.1), Fehler-Mapping (§3), Adress-Parsing (§6.3).

Datensparsamkeit ist hier hart kodiert: die Payload-Builder kennen nur die
Kontrakt-Felder. portal erhält NIE phone/address/website/notes; datenschutz
erhält NIE notes/github_repos/token_tracker_url.
"""
import re
import uuid
from datetime import datetime, timezone

import httpx

_PLZ_LINE_RE = re.compile(r"^(\d{5})\s+(.+)$")
_PLZ_SPLIT_RE = re.compile(r"\b\d{5}\s+\S")
_DOMESTIC = {"deutschland", "germany", "de", "brd"}

HANDOFF_TARGETS = ("portal", "datenschutz")


def _address_lines(address: str) -> list[str]:
    """Gleiche Heuristik wie address_format.format_address_lines, hier DB-frei
    dupliziert-schlank gehalten: mehrzeilig → Zeilen; Komma → Split; sonst vor
    der 5-stelligen PLZ trennen."""
    text = address.strip()
    if "\n" in text:
        lines = [ln.strip().rstrip(",") for ln in text.splitlines()]
    elif "," in text:
        lines = [part.strip() for part in text.split(",")]
    else:
        m = _PLZ_SPLIT_RE.search(text)
        if m and m.start() > 0:
            lines = [text[: m.start()].strip(), text[m.start():].strip()]
        else:
            lines = [text]
    return [ln for ln in lines if ln]


def parse_address(address: str | None) -> dict | None:
    """Einzeiliges Freitext-Adressfeld → {street, postal_code, city, country, raw}.

    Eindeutig (genau eine PLZ-Zeile mit Ort, davor mind. eine Straßenzeile)
    → strukturiert; unsicher → alles in `street` + Original in `raw` (§6.3).
    """
    if not address or not address.strip():
        return None
    raw = address.strip()
    lines = _address_lines(raw)

    country = "DE"
    if len(lines) > 1 and lines[-1].lower() in _DOMESTIC:
        lines = lines[:-1]

    plz_hits = [(i, _PLZ_LINE_RE.match(ln)) for i, ln in enumerate(lines)]
    plz_hits = [(i, m) for i, m in plz_hits if m]

    if len(plz_hits) == 1 and plz_hits[0][0] > 0:
        idx, m = plz_hits[0]
        street = ", ".join(lines[:idx])
        trailing = lines[idx + 1:]
        # Nachlaufende Zeilen (z. B. anderes Land) machen das Parsing unsicher —
        # außer es ist genau eine Nicht-PLZ-Zeile, die wie ein Land aussieht.
        if trailing:
            return {"street": raw, "raw": raw}
        return {
            "street": street,
            "postal_code": m.group(1),
            "city": m.group(2).strip(),
            "country": country,
            "raw": raw,
        }
    return {"street": raw, "raw": raw}


def build_envelope(customer_id: uuid.UUID | str, customer_obj: dict) -> dict:
    """Request-Envelope nach Kontrakt §3. handoff_id pro Versuch neu."""
    return {
        "handoff_id": str(uuid.uuid4()),
        "external_ref": str(customer_id),
        "source": "celox-ops",
        "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "customer": customer_obj,
    }


def _company_name(customer) -> str:
    return (customer.company or "").strip() or (customer.name or "").strip()


def build_portal_customer(
    customer,
    entitlements: list[str] | None = None,
    send_onboarding: bool = False,
) -> dict:
    """portal-Payload (§4.1) — abschließende Feldliste, KEINE weiteren Felder."""
    obj: dict = {
        "company_name": _company_name(customer),
        "lead_email": customer.email,
        "send_onboarding": bool(send_onboarding),
    }
    if customer.name and customer.name.strip():
        obj["lead_name"] = customer.name.strip()
    if entitlements:
        obj["entitlements"] = list(entitlements)
    return obj


def build_datenschutz_customer(customer, invite_contact: bool = True) -> dict:
    """datenschutz-Payload (§5.1) — abschließende Feldliste, KEINE weiteren Felder."""
    contact: dict = {
        "name": (customer.name or "").strip(),
        "email": customer.email,
    }
    if customer.phone and customer.phone.strip():
        contact["phone"] = customer.phone.strip()

    obj: dict = {
        "company_name": _company_name(customer),
        "contact": contact,
        "invite_contact": bool(invite_contact),
    }
    parsed = parse_address(customer.address)
    if parsed:
        obj["address"] = parsed
    if customer.website and customer.website.strip():
        obj["website"] = customer.website.strip()
    return obj


def field_keys(customer_obj: dict, prefix: str = "") -> list[str]:
    """Flache Liste der übergebenen Feld-KEYS (für den fachlichen Audit-Eintrag —
    bewusst keine Werte, Kontrakt §5.2/§6.5)."""
    keys: list[str] = []
    for k, v in customer_obj.items():
        if isinstance(v, dict):
            keys.extend(field_keys(v, prefix=f"{k}."))
        else:
            keys.append(f"{prefix}{k}")
    return sorted(keys)


class HandoffError(Exception):
    """Fehler beim Ziel-Call. `status` = HTTP-Code fürs Durchreichen an die UI,
    `code` = kompakter Status für §6.4 (`error:<code>`), `detail` = lesbar."""

    def __init__(self, status: int, code: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail


def map_target_response(status_code: int, body: dict | None) -> dict:
    """2xx → Ergebnis-Dict; alles andere → HandoffError nach Kontrakt §3."""
    body = body or {}
    if status_code in (200, 201):
        return body
    if status_code == 401:
        raise HandoffError(502, "401", "Ziel-App lehnt den Service-Key ab (401) — Key-Konfiguration prüfen.")
    if status_code == 409:
        reason = body.get("reason", "conflict")
        detail = body.get("detail", "")
        raise HandoffError(409, "409", f"Fachkonflikt im Ziel ({reason}): {detail}".strip().rstrip(":"))
    if status_code == 422:
        raise HandoffError(422, "422", f"Ziel-App lehnt die Daten ab (Validierung): {body.get('fields') or body}")
    if status_code == 429:
        raise HandoffError(429, "429", "Ziel-App drosselt (Rate-Limit) — kurz warten und erneut versuchen.")
    if status_code == 503:
        raise HandoffError(503, "503", "Ziel-App ist für den Handoff nicht konfiguriert (503).")
    raise HandoffError(502, str(status_code), f"Ziel-App-Fehler ({status_code}) — temporär, erneut versuchen.")


async def send_handoff(base_url: str, key: str, envelope: dict) -> dict:
    """POST /api/integration/handoff beim Ziel. Timeout 15 s, kein Retry (Kontrakt §1)."""
    url = f"{base_url.rstrip('/')}/api/integration/handoff"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json=envelope,
            )
    except httpx.TimeoutException:
        raise HandoffError(504, "timeout", "Ziel-App antwortet nicht (Timeout 15 s) — temporär, erneut versuchen.")
    except httpx.HTTPError as e:
        raise HandoffError(502, "unreachable", f"Ziel-App nicht erreichbar: {e.__class__.__name__}")
    try:
        body = resp.json()
    except ValueError:
        body = None
    return map_target_response(resp.status_code, body)
