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
    SAME_ORDER_SECONDS,
    VENDOR,
    HostingerError,
    build_drafts,
    build_notes,
    category_for,
    describe,
    domain_tld,
    external_ref,
    fetch_account,
    last_billed_on,
    match_domains,
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

    def test_tld_of_a_domain_name(self):
        assert domain_tld("mapsmate.de") == ".de"
        assert domain_tld("Nice-To-Be-Nice.WTF") == ".wtf"
        assert domain_tld("kaputt") is None

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

    def test_domain_is_named_when_one_is_assigned(self):
        assert describe(DOMAIN_SUB, {}, domain="mapsmate.de") == f"Domain mapsmate.de ({VENDOR})"

    def test_domain_stays_generic_without_an_assignment(self):
        """Lieber „.de" als ein geratener Name in einer Buchung."""
        assert describe(DOMAIN_SUB, {}) == f"Domain .de ({VENDOR})"

    def test_notes_carry_subscription_period_and_renewal(self):
        notes = build_notes(DOMAIN_SUB)
        assert "Abo AzqPS1VOB92asAHDO" in notes
        assert "Periode 1 Jahr" in notes
        assert "Nächste Verlängerung: 2027-07-04" in notes

    def test_notes_list_the_portfolio_when_nothing_could_be_assigned(self):
        notes = build_notes(DOMAIN_SUB, domains_by_tld={".de": ["villa-kinder.de", "jpaulo-bau.de"]})
        assert "villa-kinder.de" in notes
        assert "Keine Domain zuordenbar" in notes

    def test_notes_state_where_the_domain_name_comes_from(self):
        """Ein abgeleiteter Name darf später nicht wie eine API-Auskunft aussehen —
        die Herkunft steht deshalb in der Buchung selbst."""
        same_order = build_notes(DOMAIN_SUB, match={
            "domain": "mapsmate.de", "delta_seconds": 1, "confidence": "same_order"})
        assert "mapsmate.de" in same_order
        assert "dieselbe Bestellung" in same_order
        assert "verknüpft Abo und Domain nicht" in same_order

        derived = build_notes(DOMAIN_SUB, match={
            "domain": "gooooo.xyz", "delta_seconds": 433828, "confidence": "sequence"})
        assert "Bestellreihenfolge" in derived
        assert "5 Tage" in derived            # Abstand wird benannt, nicht verschwiegen
        assert "Bitte prüfen" in derived

        confirmed = build_notes(DOMAIN_SUB, match={
            "domain": "mapsmate.de", "delta_seconds": 1, "confidence": "same_order"},
            confirmed=True)
        assert "Zuordnung bestätigt" in confirmed
        assert "Bitte prüfen" not in confirmed

    def test_notes_carry_the_vps_ip(self):
        notes = build_notes(VPS_SUB, vps_by_subscription={VPS["subscription_id"]: VPS})
        assert "69.62.121.168" in notes and "celox.server" in notes

    def test_period_labels_are_german_and_plural_aware(self):
        assert period_label({"billing_period": 1, "billing_period_unit": "year"}) == "1 Jahr"
        assert period_label({"billing_period": 2, "billing_period_unit": "years"}) == "2 Jahre"
        assert period_label({"billing_period": 1, "billing_period_unit": "month"}) == "1 Monat"


# --------------------------------------------------------------------------- #
#  Welche Domain gehört zu welchem Abo?
#
#  Die API verknüpft beide Seiten nicht. Die Zeitstempel hier sind die echten
#  Werte aus dem Konto (zwei .de-Abos 92 Sekunden auseinander, zwei .wtf, ein
#  .xyz mit 5 Tagen Verzug) — genau die Fälle, an denen eine zu naive Regel
#  scheitert.
# --------------------------------------------------------------------------- #
_S = "2026-07-02T02:26:25Z"       # Abo A (.de)
_S2 = "2026-07-02T00:54:16Z"      # Abo B (.de), 92 s früher bestellt

DE_SUBS = [
    {**DOMAIN_SUB, "id": "A", "created_at": _S},
    {**DOMAIN_SUB, "id": "B", "created_at": _S2},
]
DE_DOMS = [
    {"domain": "mahnung-portal.de", "created_at": "2026-07-02T02:26:28Z"},     # +3 s zu A
    {"domain": "anmeldung-portal.de", "created_at": "2026-07-02T00:54:17Z"},   # +1 s zu B
]


class TestDomainMatching:
    def test_order_within_a_tld_decides(self):
        """Die Domain wird direkt nach dem Abo registriert — also paart die
        Reihenfolge. Am Konto gegen das kostenminimale Verfahren geprüft."""
        m = match_domains(DE_SUBS, DE_DOMS)
        assert m["A"]["domain"] == "mahnung-portal.de"
        assert m["B"]["domain"] == "anmeldung-portal.de"
        assert m["A"]["delta_seconds"] == 3
        assert m["B"]["delta_seconds"] == 1
        assert {v["confidence"] for v in m.values()} == {"same_order"}

    def test_tlds_never_mix(self):
        subs = DE_SUBS + [{**DOMAIN_SUB, "id": "W", "name": ".WTF Domain",
                           "created_at": "2026-04-05T09:36:53Z"}]
        doms = DE_DOMS + [{"domain": "nicetobenice.wtf",
                           "created_at": "2026-04-05T09:36:55Z"}]
        m = match_domains(subs, doms)
        assert m["W"]["domain"] == "nicetobenice.wtf"
        assert all(v["domain"].endswith(".de") for k, v in m.items() if k != "W")

    def test_a_late_registration_still_lands_right_but_is_flagged(self):
        """Realer Fall: gooooo.xyz wurde 5 Tage nach der Bestellung registriert.
        Die Reihenfolge stimmt weiter — die Zeile wird aber als prüfbedürftig
        markiert statt die Zuordnung stillschweigend zu behaupten."""
        sub = {**DOMAIN_SUB, "id": "X", "name": ".XYZ Domain",
               "created_at": "2025-01-23T15:32:09Z"}
        m = match_domains([sub], [{"domain": "gooooo.xyz",
                                   "created_at": "2025-01-28T15:52:39Z"}])
        assert m["X"]["domain"] == "gooooo.xyz"
        assert m["X"]["confidence"] == "sequence"
        assert m["X"]["delta_seconds"] > SAME_ORDER_SECONDS

    def test_candidates_are_offered_for_correction(self):
        m = match_domains(DE_SUBS, DE_DOMS)
        assert sorted(m["A"]["candidates"]) == ["anmeldung-portal.de", "mahnung-portal.de"]

    def test_surplus_stays_unassigned_instead_of_being_guessed(self):
        """Eine weggezogene Domain darf nicht dazu führen, dass ein Abo irgendeine
        andere zugeschrieben bekommt."""
        m = match_domains(DE_SUBS + [{**DOMAIN_SUB, "id": "C",
                                      "created_at": "2020-01-01T00:00:00Z"}], DE_DOMS)
        assert m["C"]["domain"] is None
        assert m["C"]["confidence"] == "unmatched"
        assert m["C"]["candidates"]                       # trotzdem auswählbar
        # Die belegten Paare bleiben unberührt.
        assert m["A"]["domain"] == "mahnung-portal.de"

    def test_no_timestamps_means_no_claim(self):
        m = match_domains([{**DOMAIN_SUB, "id": "A", "created_at": None}],
                          [{"domain": "irgendwas.de"}])
        assert m["A"]["domain"] is None

    def test_non_renewing_subscriptions_must_be_counted_in(self):
        """Wichtig: die Zuordnung braucht ALLE Domain-Abos, auch die nicht
        übernommenen. Fehlten sie, verschöbe sich die Reihenfolge und jede Domain
        landete beim falschen Abo."""
        subs = [DE_SUBS[1], {**DE_SUBS[0], "status": "non_renewing"}]
        out = build_drafts(subs, today=TODAY, domains=DE_DOMS)
        assert len(out["drafts"]) == 1
        assert out["drafts"][0]["domain"] == "anmeldung-portal.de"
        assert out["drafts"][0]["description"] == f"Domain anmeldung-portal.de ({VENDOR})"

    def test_confirmed_assignment_beats_the_derivation(self):
        out = build_drafts(DE_SUBS, today=TODAY, domains=DE_DOMS,
                           confirmed={"A": "anmeldung-portal.de"})
        by_id = {d["subscription_id"]: d for d in out["drafts"]}
        assert by_id["A"]["domain"] == "anmeldung-portal.de"
        assert by_id["A"]["domain_confidence"] == "confirmed"
        assert "Zuordnung bestätigt" in by_id["A"]["notes"]

    def test_draft_carries_everything_the_dialog_needs(self):
        out = build_drafts(DE_SUBS, today=TODAY, domains=DE_DOMS)
        draft = out["drafts"][0]
        assert draft["domain_confidence"] in {"same_order", "sequence", "confirmed"}
        assert isinstance(draft["domain_delta_seconds"], int)
        assert len(draft["domain_candidates"]) == 2

    def test_vps_needs_no_derivation(self):
        """Der VPS ist über die `subscription_id` belegt — er darf nie in die
        Domain-Zuordnung geraten."""
        m = match_domains([VPS_SUB], DE_DOMS)
        assert m == {}


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
        """Ohne Zeitstempel im Portfolio ist keine Zuordnung belegbar — dann steht
        die TLD-Liste in der Notiz, damit man selbst zuordnen kann."""
        out = build_drafts([DOMAIN_SUB], today=TODAY, domains=DOMAINS)
        notes = out["drafts"][0]["notes"]
        assert "villa-kinder.de" in notes and "jpaulo-bau.de" in notes
        assert "mixupp.com" not in notes          # andere TLD
        assert out["drafts"][0]["domain"] is None

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
