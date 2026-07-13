"""Eigener Nutzungszähler für Google Places (CLAUDE.md — Lead-Suche).
Google liefert das Restkontingent per API-Key nicht; wir zählen die selbst
ausgelösten Suchen pro Kalendermonat mit (UTC)."""
from datetime import datetime, timezone


def current_period(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


def calls_this_month(period: str | None, calls: int, now_period: str | None = None) -> int:
    """Gespeicherter Zählerstand, aber 0 wenn er aus einem früheren Monat stammt."""
    return int(calls or 0) if period == (now_period or current_period()) else 0


def bump(period: str | None, calls: int, now_period: str | None = None,
         increment: int = 1) -> tuple[str, int]:
    """Nach einer Suche: (neuer_period, neuer_zählerstand). `increment` = Anzahl
    echter API-Calls (Google: Text-Suche + Place-Details). Reset bei Monatswechsel."""
    p = now_period or current_period()
    inc = max(1, int(increment or 1))
    return (p, (int(calls or 0) + inc) if period == p else inc)


def mask_key(key: str | None) -> str | None:
    """Maskierter Hinweis für die UI (nie den Rohschlüssel zurückgeben)."""
    if not key:
        return None
    tail = key[-4:] if len(key) >= 4 else key
    return "••••" + tail
