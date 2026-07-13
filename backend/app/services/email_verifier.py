"""Abgestufte E-Mail-Qualitätsprüfung für Leads — OHNE SMTP.

Bewusst kein SMTP RCPT/Catch-all: ausgehender Port 25 ist vom VPS blockiert
(→ jede Adresse würde UNKNOWN), und RCPT-Proben von der Mail-IP würden die
Zustell-Reputation von celox.io (Rechnungen/Reminder) gefährden. Stattdessen die
sicheren, aussagekräftigen Ebenen:

    Syntax → Normalisierung → Disposable → Rolle → MX (DNS)

Ergebnis ist ein einzelner `EmailStatus` (fürs Badge + den Pipeline-Filter) plus
Gründe. `classify_syntax` ist netzfrei/rein testbar; `verify_email` nimmt einen
injizierbaren MX-Resolver (Tests mocken ihn, Bulk-Aufrufe teilen sich einen
Domain-Cache).

Deps: email-validator (bereits vorhanden), dnspython (transitiv).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field

import dns.asyncresolver
import dns.exception
import dns.resolver
from email_validator import EmailNotValidError, validate_email

# Wegwerf-Provider (Auszug; in Produktion aus gepflegter Liste ladbar).
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "getnada.com",
    "temp-mail.org", "sharklasers.com", "maildrop.cc", "fakeinbox.com",
    "dispostable.com", "mailnesia.com", "mvrht.net", "spam4.me", "moakt.com",
}

# Rollen-Adressen: existieren fast immer, sind aber selten persönliche Empfänger.
ROLE_LOCALPARTS = {
    "admin", "administrator", "info", "support", "sales", "contact", "office",
    "hello", "help", "abuse", "postmaster", "webmaster", "noreply", "no-reply",
    "billing", "team", "marketing", "hr", "jobs", "career", "careers", "service",
    "kontakt", "vertrieb", "buchhaltung", "empfang", "mail",
}


class EmailStatus(str, enum.Enum):
    VALID = "valid"                   # Syntax ok + MX vorhanden (so weit prüfbar zustellbar)
    ROLE = "role"                     # wie valid, aber Rollen-Adresse (info@, support@ …)
    DISPOSABLE = "disposable"         # Wegwerf-Provider
    NO_MX = "no_mx"                   # Domain nimmt keine Mail an
    INVALID_SYNTAX = "invalid_syntax"  # Format ungültig
    UNKNOWN = "unknown"               # DNS temporär nicht auflösbar / keine E-Mail


# Für den Pipeline-Filter „problematische E-Mail".
PROBLEM_STATUSES = {EmailStatus.DISPOSABLE, EmailStatus.NO_MX, EmailStatus.INVALID_SYNTAX}


class MxUnknown(Exception):
    """Transienter DNS-Fehler (Timeout/NoNameservers) → Status UNKNOWN, nicht NO_MX."""


@dataclass
class EmailCheck:
    status: EmailStatus
    normalized: str | None = None
    is_role: bool = False
    is_disposable: bool = False
    mx_host: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class _Syntax:
    ok: bool
    normalized: str | None = None
    domain: str | None = None
    local: str | None = None
    is_role: bool = False
    is_disposable: bool = False
    error: str | None = None


def classify_syntax(email: str | None) -> _Syntax:
    """Rein/netzfrei: Syntax + Normalisierung + Rollen-/Disposable-Erkennung."""
    try:
        info = validate_email((email or "").strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        return _Syntax(ok=False, error=str(exc))
    domain = info.domain.lower()
    local = info.local_part.lower()
    return _Syntax(
        ok=True, normalized=info.normalized, domain=domain, local=local,
        is_role=local in ROLE_LOCALPARTS, is_disposable=domain in DISPOSABLE_DOMAINS,
    )


async def resolve_mx(domain: str, timeout: float = 3.0) -> list[str]:
    """MX-Hosts nach Priorität; A-Record als impliziter Mailserver (RFC 5321).
    Rückgabe [] = definitiv keine Mail-Annahme. Raises MxUnknown bei transientem
    DNS-Fehler (Timeout/NoNameservers)."""
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = await resolver.resolve(domain, "MX")
        hosts = sorted(answers, key=lambda r: r.preference)
        return [str(r.exchange).rstrip(".") for r in hosts]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        try:
            await resolver.resolve(domain, "A")
            return [domain]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
            raise MxUnknown(str(exc)) from exc
        except dns.exception.DNSException:
            return []
    except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
        raise MxUnknown(str(exc)) from exc
    except dns.exception.DNSException:
        return []


async def verify_email(email: str | None, *, resolve=resolve_mx,
                       mx_cache: dict | None = None) -> EmailCheck:
    """Vollständige (SMTP-freie) Prüfung. `resolve` ist injizierbar (Tests);
    `mx_cache` (domain→hosts|None) teilt DNS-Ergebnisse über einen Batch."""
    syn = classify_syntax(email)
    if not syn.ok:
        return EmailCheck(status=EmailStatus.INVALID_SYNTAX,
                          reasons=[f"Syntax ungültig: {syn.error}"])
    reasons: list[str] = []
    if syn.is_disposable:
        return EmailCheck(status=EmailStatus.DISPOSABLE, normalized=syn.normalized,
                          is_role=syn.is_role, is_disposable=True,
                          reasons=["Wegwerf-Provider"])
    if syn.is_role:
        reasons.append("Rollen-Adresse (info@, support@ …) — selten persönlich")

    # MX-Lookup (Cache über den Batch)
    hosts: list[str] | None
    if mx_cache is not None and syn.domain in mx_cache:
        hosts = mx_cache[syn.domain]
    else:
        try:
            hosts = await resolve(syn.domain)
        except MxUnknown:
            hosts = None            # transient → UNKNOWN
        if mx_cache is not None:
            mx_cache[syn.domain] = hosts

    if hosts is None:
        reasons.append("DNS temporär nicht auflösbar")
        return EmailCheck(status=EmailStatus.UNKNOWN, normalized=syn.normalized,
                          is_role=syn.is_role, reasons=reasons)
    if not hosts:
        reasons.append("Kein MX-/A-Record — Domain nimmt keine Mail an")
        return EmailCheck(status=EmailStatus.NO_MX, normalized=syn.normalized,
                          is_role=syn.is_role, reasons=reasons)

    reasons.append("Syntax ok + MX vorhanden")
    status = EmailStatus.ROLE if syn.is_role else EmailStatus.VALID
    return EmailCheck(status=status, normalized=syn.normalized, is_role=syn.is_role,
                      mx_host=hosts[0], reasons=reasons)
