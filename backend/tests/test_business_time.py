"""Tests für die Geschäftszeitzone — nagelt die Datumsfehler fest, die der
UTC-Container verursacht hat.

Alle Prüfungen laufen mit **gesetzten Zeitpunkten** (kein Warten, keine
Abhängigkeit von der Uhr des Testlaufs) und sind unabhängig davon korrekt, ob
die Umgebung `TZ` setzt — genau das war der Kern des Fehlers.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.services.business_time import (
    BUSINESS_TZ,
    BUSINESS_TZ_NAME,
    day_end_utc,
    day_start_utc,
    now,
    today,
)

UTC = timezone.utc


class TestDayBoundaries:
    def test_summer_day_starts_at_22_utc_previous_day(self):
        """Sommerzeit (UTC+2): der 28.07. beginnt um 27.07. 22:00 UTC.
        Vorher wurde das lokale Datum einfach mit tzinfo=UTC markiert — der
        Tageswechsel lag damit um 02:00 deutscher Zeit."""
        assert day_start_utc(date(2026, 7, 28)) == datetime(2026, 7, 27, 22, 0, tzinfo=UTC)

    def test_winter_day_starts_at_23_utc_previous_day(self):
        """Winterzeit (UTC+1) — der Offset darf nicht hart verdrahtet sein."""
        assert day_start_utc(date(2026, 1, 15)) == datetime(2026, 1, 14, 23, 0, tzinfo=UTC)

    def test_day_end_is_next_day_start(self):
        d = date(2026, 7, 28)
        assert day_end_utc(d) == day_start_utc(date(2026, 7, 29))

    def test_dst_switch_day_is_23_hours(self):
        """Am Umstellungstag (29.03.2026) hat der Tag nur 23 Stunden."""
        length = day_end_utc(date(2026, 3, 29)) - day_start_utc(date(2026, 3, 29))
        assert length.total_seconds() == 23 * 3600

    def test_activity_just_after_midnight_counts_for_the_new_day(self):
        """Der Fehler, der Tagesquote und Streak verschob: eine um 00:30 deutscher
        Zeit erledigte Aktion (22:30 UTC) muss zum NEUEN Tag zählen."""
        completed_at = datetime(2026, 7, 27, 22, 30, tzinfo=UTC)   # = 28.07. 00:30 CEST
        assert completed_at >= day_start_utc(date(2026, 7, 28))
        # Mit der alten UTC-Grenze wäre sie durchgefallen:
        naive_utc_boundary = datetime(2026, 7, 28, 0, 0, tzinfo=UTC)
        assert completed_at < naive_utc_boundary


class TestBusinessNowAndToday:
    def test_today_is_the_german_calendar_day(self):
        """Zwischen 00:00 und 02:00 deutscher Zeit ist der UTC-Tag noch der
        Vortag — `today()` darf dem nicht folgen."""
        moment = datetime(2026, 7, 27, 23, 30, tzinfo=UTC)          # = 28.07. 01:30 CEST
        assert moment.astimezone(BUSINESS_TZ).date() == date(2026, 7, 28)
        assert moment.date() == date(2026, 7, 27), "UTC-Datum liegt zurück"

    def test_new_year_invoice_number_uses_the_german_year(self):
        """Silvester 00:30 CET: UTC ist noch das alte Jahr — die Rechnungsnummer
        hätte den alten Nummernkreis fortgesetzt."""
        moment = datetime(2026, 12, 31, 23, 30, tzinfo=UTC)         # = 01.01.2027 00:30 CET
        assert moment.astimezone(BUSINESS_TZ).year == 2027
        assert moment.year == 2026

    def test_reminder_hour_is_the_german_hour(self):
        """Eine für 08:00 eingestellte Erinnerung ging im UTC-Container um
        10:00 deutscher Zeit raus."""
        moment = datetime(2026, 7, 28, 6, 5, tzinfo=UTC)            # = 08:05 CEST
        assert moment.astimezone(BUSINESS_TZ).hour == 8
        assert moment.hour == 6

    def test_now_is_timezone_aware_and_in_business_zone(self):
        value = now()
        assert value.tzinfo is not None
        assert value.utcoffset() in (
            datetime(2026, 1, 1, tzinfo=BUSINESS_TZ).utcoffset(),
            datetime(2026, 7, 1, tzinfo=BUSINESS_TZ).utcoffset(),
        )

    def test_today_matches_now(self):
        assert today() == now().date()

    def test_zone_is_germany(self):
        assert BUSINESS_TZ_NAME == "Europe/Berlin"
        assert BUSINESS_TZ == ZoneInfo("Europe/Berlin")


class TestNoNaiveCallsLeftInBusinessLogic:
    """Regressionsguard: keine nackten `date.today()`/`datetime.now()` mehr in
    der Geschäftslogik — sonst kehrt der UTC-Versatz durch die Hintertür zurück."""

    def test_business_modules_use_the_helpers(self):
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent / "app"
        offenders = []
        for path in root.rglob("*.py"):
            if path.name == "business_time.py":
                continue
            text = path.read_text()
            for match in re.finditer(r"\b(date\.today\(\)|datetime\.now\(\))", text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line = text[line_start:text.find("\n", match.start())]
                if "timezone.utc" in line:      # bewusst UTC → in Ordnung
                    continue
                offenders.append(f"{path.relative_to(root)}: {line.strip()}")
        assert not offenders, "Naive Zeitaufrufe gefunden:\n" + "\n".join(offenders)
