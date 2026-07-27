"""Geschäftszeitzone — eine Quelle für „heute" und „jetzt".

**Das Problem:** der Container läuft in UTC. `date.today()` liefert damit zwischen
00:00 und 02:00 deutscher Sommerzeit noch den **Vortag**, und `datetime.now().hour`
ist die UTC-Stunde. Konkrete Folgen waren: die Erinnerungsmail für 08:00 ging um
10:00 raus, eine Schnellrechnung um 00:30 trug das Datum von gestern, To-dos
galten zwei Stunden zu früh als überfällig, Tagesquote und Streak wechselten um
02:00 statt um Mitternacht, und in der Silvesternacht hätte eine Rechnung die
Nummer des alten Jahres bekommen.

**Die Lösung:** Datums- und Uhrzeitlogik läuft über diese Helfer und ist damit
**unabhängig von der Container-Konfiguration** korrekt. `TZ=Europe/Berlin` wird
zusätzlich gesetzt (Logs, Dateinamen, Fremdbibliotheken), ist aber keine
Voraussetzung mehr für richtige Geschäftsdaten.

Deutschland ist die einzige Geschäftszeitzone (Rechnungen, USt, EÜR, Fristen) —
daher eine feste Zone statt einer Nutzereinstellung.

**Regel:** In Geschäftslogik nie `date.today()`/`datetime.now()` direkt
verwenden, sondern `today()`/`now()` von hier. Für DB-Vergleiche gegen
`timestamptz`-Spalten `day_start_utc()` nutzen — ein lokales Mitternacht-Datum
mit `tzinfo=timezone.utc` zu markieren ist um den UTC-Offset falsch.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

BUSINESS_TZ_NAME = "Europe/Berlin"
BUSINESS_TZ = ZoneInfo(BUSINESS_TZ_NAME)


def now() -> datetime:
    """Jetzt in der Geschäftszeitzone (zeitzonenbewusst)."""
    return datetime.now(BUSINESS_TZ)


def today() -> date:
    """Heutiges Geschäftsdatum (deutscher Kalendertag, nicht der UTC-Tag)."""
    return now().date()


def day_start_utc(d: date) -> datetime:
    """Beginn des Geschäftstages `d` als UTC-Zeitpunkt — für Vergleiche gegen
    `timestamptz`-Spalten.

    Beispiel: 2026-07-28 in Sommerzeit → 2026-07-27T22:00:00+00:00.
    """
    return datetime.combine(d, time.min, tzinfo=BUSINESS_TZ).astimezone(timezone.utc)


def day_end_utc(d: date) -> datetime:
    """Ende des Geschäftstages `d` (exklusiv) als UTC-Zeitpunkt."""
    return day_start_utc(d + timedelta(days=1))


def container_timezone_ok() -> bool:
    """Ist die Container-Zeitzone die Geschäftszeitzone?

    Nur informativ (z. B. für `/api/health`): die Geschäftslogik ist über die
    Helfer oben schon unabhängig davon korrekt. Eine Abweichung betrifft noch
    Logzeitstempel und Bibliotheken, die `localtime` verwenden.
    """
    local_offset = datetime.now().astimezone().utcoffset()
    return local_offset == now().utcoffset()
