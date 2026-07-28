"""DB-/netzfreie Tests für den Hostinger-Kostenimport.

Die Abbildung ist rein, deshalb lässt sich hier alles prüfen, was schiefgehen
kann — und die Fallstricke sind echte, am Konto beobachtete Fälle, keine
erfundenen: Preise in Cent, ein Verlängerungstermin mit mehr als einer Periode
Abstand, generische Domain-Namen.
"""
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.models.expense import ExpenseCategory
from app.services.hostinger import (
    VENDOR,
    HostingerError,
    build_drafts,
    build_notes,
    category_for,
    describe,
    external_ref,
    fetch_account,
    last_billed_on,
    parse_price_cents,
    period_label,
    shift_back,
    tld_of,
    to_expense,
    total_of,
)

TODAY = date(2026, 7, 28)

# Struktur wörtlich wie von der API geliefert (am Konto geprüft).
DOMAIN_SUB = {
    "id": "AzqPS1VOB92asAHDO", "name": ".DE Domain", "status": "active",
    "billing_period": 1, "billing_period_unit": "year", "currency_code": "EUR",
    "total_price": 1199, "renewal_price": 1199, "is_auto_renewed": True,
    "created_at": "2026-07-02T02:26:25Z", "expires_at": None,
    "next_billing_at": "2027-07-04T23:59:59Z",
}
VPS_SUB = {
    "id": "AzqS7AUfmguhR1qqg", "name": "KVM 4", "status": "active",
    "billing_period": 1, "billing_period_unit": "month", "currency_code": "EUR",
    "total_price": 2999, "renewal_price": 2999, "is_auto_renewed": True,
    "created_at": "2025-03-18T08:53:26Z", "expires_at": None,
    "next_billing_at": "2026-08-15T23:59:59Z",
}
VPS = {"id": 759942, "subscription_id": "AzqS7AUfmguhR1qqg", "plan": "KVM 4",
       "hostname": "celox.server", "ipv4": [{"address": "69.62.121.168"}]}
DOMAINS = [{"domain": "villa-kinder.de"}, {"domain": "jpaulo-bau.de"},
           {"domain": "mixupp.com"}]


# --------------------------------------------------------------------------- #
#  Preise stehen in Cent
# --------------------------------------------------------------------------- #
class TestPrices:
    def test_cents_become_euro(self):
        """`1199` heißt 11,99 € — ohne Division wäre jede Ausgabe 100× zu hoch."""
        assert parse_price_cents(1199) == Decimal("11.99")
        assert parse_price_cents(6399) == Decimal("63.99")
        assert parse_price_cents(2999) == Decimal("29.99")
        assert parse_price_cents(0) == Decimal("0.00")

    def test_unusable_values_are_refused_not_guessed(self):
        for bad in (None, "", "kostenlos", -100, True, {}):
            assert parse_price_cents(bad) is None

    def test_renewal_price_wins_over_total(self):
        """Der Verlängerungspreis ist der künftige Aufwand; `total_price` kann
        einen Einführungsrabatt enthalten."""
        sub = {**DOMAIN_SUB, "total_price": 99, "renewal_price": 1199}
        assert to_expense(sub, today=TODAY)["amount"] == "11.99"

    def test_total_price_is_the_fallback(self):
        sub = {**DOMAIN_SUB, "renewal_price": None, "total_price": 1199}
        assert to_expense(sub, today=TODAY)["amount"] == "11.99"

    def test_total_of_sums_decimals(self):
        assert total_of([{"amount": "11.99"}, {"amount": "63.99"}]) == Decimal("75.98")
        assert total_of([{"amount": "x"}, {}]) == Decimal("0.00")


# --------------------------------------------------------------------------- #
#  Datum der letzten Abrechnung
# --------------------------------------------------------------------------- #
class TestLastBilled:
    def test_one_period_before_the_next_billing(self):
        assert last_billed_on(DOMAIN_SUB, TODAY) == date(2026, 7, 4)

    def test_future_candidate_goes_back_another_period(self):
        """Echter Fall im Konto: Registrierung 2025-08-29, nächste Abrechnung
        2027-07-31. Minus eine Periode wäre 2026-07-31 — drei Tage in der
        ZUKUNFT, also noch nicht abgerechnet. Richtig ist der Vertragsbeginn."""
        sub = {**DOMAIN_SUB, "created_at": "2025-08-29T00:00:00Z",
               "next_billing_at": "2027-07-31T23:59:59Z"}
        assert last_billed_on(sub, TODAY) == date(2025, 8, 29)

    def test_never_before_the_contract_started(self):
        sub = {**DOMAIN_SUB, "created_at": "2026-07-02T00:00:00Z",
               "next_billing_at": "2026-08-01T00:00:00Z", "billing_period_unit": "month"}
        assert last_billed_on(sub, TODAY) == date(2026, 7, 2)

    def test_never_in_the_future(self):
        """Eine noch nicht geflossene Zahlung gehört nicht in die EÜR."""
        sub = {**DOMAIN_SUB, "created_at": "2026-07-20T00:00:00Z",
               "next_billing_at": "2027-07-20T00:00:00Z"}
        assert last_billed_on(sub, TODAY) <= TODAY

    def test_without_next_billing_the_start_date_counts(self):
        sub = {**DOMAIN_SUB, "next_billing_at": None,
               "created_at": "2025-04-05T09:36:53Z"}
        assert last_billed_on(sub, TODAY) == date(2025, 4, 5)

    def test_no_dates_at_all_yields_none(self):
        assert last_billed_on({"id": "x"}, TODAY) is None

    def test_broken_dates_do_not_crash(self):
        assert last_billed_on({"created_at": "gestern", "next_billing_at": "bald"}, TODAY) is None

    def test_loop_is_bounded_against_broken_data(self):
        """Ein absurd weit entfernter Termin darf nicht endlos zurückrechnen."""
        sub = {**DOMAIN_SUB, "created_at": "2020-01-01T00:00:00Z",
               "next_billing_at": "2400-01-01T00:00:00Z"}
        assert last_billed_on(sub, TODAY) is not None


class TestShiftBack:
    def test_years_and_months(self):
        assert shift_back(date(2027, 7, 4), 1, "year") == date(2026, 7, 4)
        assert shift_back(date(2026, 8, 15), 1, "month") == date(2026, 7, 15)
        assert shift_back(date(2026, 1, 15), 1, "month") == date(2025, 12, 15)

    def test_month_end_is_clamped(self):
        """31.03. minus einen Monat ist der 28.02., nicht ein ungültiges Datum."""
        assert shift_back(date(2026, 3, 31), 1, "month") == date(2026, 2, 28)
        assert shift_back(date(2028, 3, 31), 1, "month") == date(2028, 2, 29)  # Schaltjahr

    def test_leap_day_minus_one_year(self):
        assert shift_back(date(2028, 2, 29), 1, "year") == date(2027, 2, 28)

    def test_days_weeks_and_plural_units(self):
        assert shift_back(date(2026, 7, 28), 7, "days") == date(2026, 7, 21)
        assert shift_back(date(2026, 7, 28), 2, "weeks") == date(2026, 7, 14)
        assert shift_back(date(2027, 7, 4), 1, "years") == date(2026, 7, 4)

    def test_zero_or_missing_count_is_treated_as_one(self):
        assert shift_back(date(2026, 8, 15), 0, "month") == date(2026, 7, 15)


# --------------------------------------------------------------------------- #
#  Kategorien, Beschreibung, Notizen
# --------------------------------------------------------------------------- #
class TestMapping:
    def test_tld_detection(self):
        assert tld_of(".DE Domain") == ".de"
        assert tld_of(".CAMP Domain") == ".camp"
        assert tld_of("KVM 4") is None
        assert tld_of("") is None

    def test_categories(self):
        assert category_for(".DE Domain") is ExpenseCategory.domain
        assert category_for("KVM 4") is ExpenseCategory.hosting
        assert category_for("Business Web Hosting") is ExpenseCategory.hosting
        # Unbekanntes wird nicht in eine Kategorie geraten.
        assert category_for("Irgendein Zusatz") is ExpenseCategory.sonstige

    def test_vps_is_named_exactly_because_the_mapping_is_proven(self):
        """Die VPS-Liste nennt ihre `subscription_id` — das ist eine belegte
        Zuordnung, also darf Plan und Hostname in die Beschreibung."""
        text = describe(VPS_SUB, {VPS["subscription_id"]: VPS})
        assert text == f"VPS KVM 4 · celox.server ({VENDOR})"

    def test_domains_stay_generic_because_the_api_does_not_say_which(self):
        assert describe(DOMAIN_SUB, {}) == f"Domain .de ({VENDOR})"

    def test_notes_carry_subscription_period_and_renewal(self):
        notes = build_notes(DOMAIN_SUB)
        assert "Abo AzqPS1VOB92asAHDO" in notes
        assert "Periode 1 Jahr" in notes
        assert "Nächste Verlängerung: 2027-07-04" in notes

    def test_notes_list_the_portfolio_of_that_tld_and_admit_the_gap(self):
        notes = build_notes(DOMAIN_SUB, domains_by_tld={".de": ["villa-kinder.de", "jpaulo-bau.de"]})
        assert "villa-kinder.de" in notes
        assert "sagt nicht, welche Domain" in notes

    def test_notes_carry_the_vps_ip(self):
        notes = build_notes(VPS_SUB, vps_by_subscription={VPS["subscription_id"]: VPS})
        assert "69.62.121.168" in notes and "celox.server" in notes

    def test_period_labels_are_german_and_plural_aware(self):
        assert period_label({"billing_period": 1, "billing_period_unit": "year"}) == "1 Jahr"
        assert period_label({"billing_period": 2, "billing_period_unit": "years"}) == "2 Jahre"
        assert period_label({"billing_period": 1, "billing_period_unit": "month"}) == "1 Monat"


# --------------------------------------------------------------------------- #
#  Idempotenz
# --------------------------------------------------------------------------- #
class TestIdempotency:
    def test_ref_contains_subscription_and_period(self):
        ref = external_ref(DOMAIN_SUB, date(2026, 7, 4))
        assert ref == "hostinger:AzqPS1VOB92asAHDO:2026-07-04"

    def test_same_period_yields_the_same_ref(self):
        assert external_ref(DOMAIN_SUB, date(2026, 7, 4)) == \
               external_ref(dict(DOMAIN_SUB), date(2026, 7, 4))

    def test_next_year_is_a_new_ref(self):
        """Die Verlängerung im nächsten Jahr MUSS importierbar sein — nur
        derselbe Zeitraum nicht zweimal."""
        assert external_ref(DOMAIN_SUB, date(2026, 7, 4)) != \
               external_ref(DOMAIN_SUB, date(2027, 7, 4))


# --------------------------------------------------------------------------- #
#  Gesamtlauf
# --------------------------------------------------------------------------- #
class TestBuildDrafts:
    def test_only_active_subscriptions_become_expenses(self):
        subs = [DOMAIN_SUB, {**DOMAIN_SUB, "id": "B", "status": "non_renewing"}]
        out = build_drafts(subs, today=TODAY)
        assert len(out["drafts"]) == 1
        assert any("non_renewing" in s for s in out["skipped"])

    def test_nothing_is_dropped_silently(self):
        """Jeder übersprungene Eintrag wird benannt — stilles Weglassen wäre der
        schlimmere Fehler."""
        subs = [
            {**DOMAIN_SUB, "id": "A", "status": "expired"},
            {**DOMAIN_SUB, "id": "B", "renewal_price": None, "total_price": None},
            {**DOMAIN_SUB, "id": "C", "currency_code": "USD"},
        ]
        out = build_drafts(subs, today=TODAY)
        assert out["drafts"] == []
        assert len(out["skipped"]) == 3
        assert any("USD" in s for s in out["skipped"])
        assert any("kein belegter Betrag" in s for s in out["skipped"])

    def test_vps_and_domain_together(self):
        out = build_drafts([DOMAIN_SUB, VPS_SUB], today=TODAY,
                           domains=DOMAINS, vps=[VPS])
        by_cat = {d["category"]: d for d in out["drafts"]}
        assert by_cat["hosting"]["description"] == f"VPS KVM 4 · celox.server ({VENDOR})"
        assert by_cat["hosting"]["amount"] == "29.99"
        assert by_cat["domain"]["amount"] == "11.99"
        assert all(d["vendor"] == VENDOR and d["recurring"] is True for d in out["drafts"])

    def test_domain_portfolio_is_grouped_by_tld(self):
        out = build_drafts([DOMAIN_SUB], today=TODAY, domains=DOMAINS)
        notes = out["drafts"][0]["notes"]
        assert "villa-kinder.de" in notes and "jpaulo-bau.de" in notes
        assert "mixupp.com" not in notes          # andere TLD

    def test_newest_first(self):
        older = {**DOMAIN_SUB, "id": "old", "next_billing_at": "2027-01-04T00:00:00Z"}
        out = build_drafts([older, DOMAIN_SUB], today=TODAY)
        assert out["drafts"][0]["date"] >= out["drafts"][1]["date"]

    def test_garbage_entries_are_ignored(self):
        out = build_drafts([DOMAIN_SUB, "kaputt", None, 42], today=TODAY)
        assert len(out["drafts"]) == 1


# --------------------------------------------------------------------------- #
#  HTTP-Schicht (gefakter Transport, kein Netz)
# --------------------------------------------------------------------------- #
class TestFetch:
    def _client(self, handler):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    @pytest.mark.asyncio
    async def test_happy_path_collects_all_three_lists(self):
        def handler(request):
            assert request.headers["authorization"] == "Bearer geheim"
            if "subscriptions" in request.url.path:
                return httpx.Response(200, json=[DOMAIN_SUB])
            if "portfolio" in request.url.path:
                return httpx.Response(200, json=DOMAINS)
            return httpx.Response(200, json=[VPS])

        async with self._client(handler) as client:
            out = await fetch_account("geheim", client)
        assert len(out["subscriptions"]) == 1 and len(out["domains"]) == 3 and len(out["vps"]) == 1

    @pytest.mark.asyncio
    async def test_rejected_key_gives_an_actionable_message(self):
        async with self._client(lambda r: httpx.Response(401, json={"message": "x"})) as client:
            with pytest.raises(HostingerError) as exc:
                await fetch_account("falsch", client)
        assert "API-Key" in str(exc.value) and "hPanel" in str(exc.value)

    @pytest.mark.asyncio
    async def test_rate_limit_is_named(self):
        async with self._client(lambda r: httpx.Response(429)) as client:
            with pytest.raises(HostingerError, match="drosselt"):
                await fetch_account("k", client)

    @pytest.mark.asyncio
    async def test_enrichment_may_fail_without_killing_the_import(self):
        """Portfolio und VPS-Liste sind Beigabe — nur die Abos sind Pflicht."""
        def handler(request):
            if "subscriptions" in request.url.path:
                return httpx.Response(200, json=[DOMAIN_SUB])
            return httpx.Response(500)

        async with self._client(handler) as client:
            out = await fetch_account("k", client)
        assert len(out["subscriptions"]) == 1
        assert out["domains"] == [] and out["vps"] == []

    @pytest.mark.asyncio
    async def test_network_failure_is_reported_in_plain_words(self):
        def handler(request):
            raise httpx.ConnectError("weg")

        async with self._client(handler) as client:
            with pytest.raises(HostingerError, match="nicht erreichbar"):
                await fetch_account("k", client)

    @pytest.mark.asyncio
    async def test_unexpected_shape_is_refused(self):
        async with self._client(lambda r: httpx.Response(200, json={"oops": 1})) as client:
            with pytest.raises(HostingerError, match="Abo-Liste"):
                await fetch_account("k", client)
