"""DB-freie Tests für den Customer-Handoff (services/handoff_service.py).

Kern-Garantien aus dem Kontrakt (_integration/customer-handoff-contract.md):
- Adress-Parser §6.3 (Komma, PLZ-Grenze, mehrzeilig, Deutschland-Suffix, unsicher→raw)
- Feld-Whitelists §4.1/§5.1 — portal NIE phone/address/website/notes,
  datenschutz NIE notes/github_repos/token_tracker_url
- Envelope §3, Fehler-Mapping §3
"""
import uuid
from types import SimpleNamespace

import pytest

from app.services.handoff_service import (
    HandoffError,
    build_datenschutz_customer,
    build_envelope,
    build_portal_customer,
    field_keys,
    map_target_response,
    parse_address,
)


def _customer(**overrides):
    base = dict(
        id=uuid.uuid4(),
        name="Max Beispiel",
        email="gf@beispiel.de",
        phone="+49 30 1234567",
        company="Beispiel GmbH",
        address="Musterstr. 1, 12053 Berlin",
        website="https://beispiel.de",
        github_repos="pepperonas/beispiel",
        token_tracker_url='[{"url":"https://tracker"}]',
        notes="Sehr geheime interne Notiz",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------- parse_address

class TestParseAddress:
    def test_comma_separated(self):
        p = parse_address("Musterstr. 1, 12053 Berlin")
        assert p == {
            "street": "Musterstr. 1",
            "postal_code": "12053",
            "city": "Berlin",
            "country": "DE",
            "raw": "Musterstr. 1, 12053 Berlin",
        }

    def test_plz_boundary_without_comma(self):
        p = parse_address("Max-Planck-Straße 5a 60486 Frankfurt am Main")
        assert p["street"] == "Max-Planck-Straße 5a"
        assert p["postal_code"] == "60486"
        assert p["city"] == "Frankfurt am Main"

    def test_multiline(self):
        p = parse_address("Hauptstraße 24\n35510 Butzbach")
        assert p["street"] == "Hauptstraße 24"
        assert p["postal_code"] == "35510"
        assert p["city"] == "Butzbach"

    def test_trailing_deutschland_dropped(self):
        p = parse_address("Musterstr. 1, 12053 Berlin, Deutschland")
        assert p["postal_code"] == "12053"
        assert p["city"] == "Berlin"
        assert p["country"] == "DE"

    def test_hyphens_intact(self):
        p = parse_address("Kurt-Schumacher-Str. 5-7, 10117 Berlin")
        assert p["street"] == "Kurt-Schumacher-Str. 5-7"
        assert p["city"] == "Berlin"

    def test_unparsable_goes_to_street_and_raw(self):
        raw = "Gewerbegebiet Süd, Halle 3"
        p = parse_address(raw)
        assert p == {"street": raw, "raw": raw}

    def test_plz_only_no_street_is_unsure(self):
        p = parse_address("12053 Berlin")
        assert p == {"street": "12053 Berlin", "raw": "12053 Berlin"}

    def test_foreign_country_suffix_is_unsure(self):
        # Nachlaufende Nicht-Deutschland-Zeile → unsicher, nichts raten
        raw = "Rue Exemple 1, 75001 Paris, Frankreich"
        p = parse_address(raw)
        assert p["street"] == raw
        assert "postal_code" not in p

    def test_multi_street_lines_joined(self):
        p = parse_address("c/o Kanzlei Meyer, Musterstr. 1, 12053 Berlin")
        assert p["street"] == "c/o Kanzlei Meyer, Musterstr. 1"
        assert p["postal_code"] == "12053"

    def test_empty_and_none(self):
        assert parse_address(None) is None
        assert parse_address("   ") is None


# ------------------------------------------------------------- Payload-Builder

class TestPortalPayload:
    def test_whitelist_only(self):
        obj = build_portal_customer(_customer(), entitlements=["training:security"], send_onboarding=True)
        assert set(obj) <= {"company_name", "lead_email", "lead_name", "entitlements", "send_onboarding"}

    def test_never_contains_phone_address_website_notes(self):
        obj = build_portal_customer(_customer())
        flat = str(obj)
        for forbidden in ("phone", "address", "website", "notes", "github", "token_tracker"):
            assert forbidden not in obj
            assert forbidden not in flat
        assert "Sehr geheime interne Notiz" not in flat
        assert "+49 30 1234567" not in flat

    def test_company_fallback_to_name(self):
        obj = build_portal_customer(_customer(company=None))
        assert obj["company_name"] == "Max Beispiel"
        obj2 = build_portal_customer(_customer(company="  "))
        assert obj2["company_name"] == "Max Beispiel"

    def test_send_onboarding_default_false(self):
        assert build_portal_customer(_customer())["send_onboarding"] is False

    def test_entitlements_omitted_when_empty(self):
        assert "entitlements" not in build_portal_customer(_customer(), entitlements=[])


class TestDatenschutzPayload:
    def test_whitelist_only(self):
        obj = build_datenschutz_customer(_customer())
        assert set(obj) <= {"company_name", "contact", "address", "website", "invite_contact"}
        assert set(obj["contact"]) <= {"name", "email", "phone"}

    def test_never_contains_notes_repos_tracker(self):
        obj = build_datenschutz_customer(_customer())
        flat = str(obj)
        for forbidden in ("notes", "github", "token_tracker"):
            assert forbidden not in flat
        assert "Sehr geheime interne Notiz" not in flat

    def test_contact_and_address_mapping(self):
        obj = build_datenschutz_customer(_customer())
        assert obj["contact"] == {"name": "Max Beispiel", "email": "gf@beispiel.de", "phone": "+49 30 1234567"}
        assert obj["address"]["postal_code"] == "12053"
        assert obj["website"] == "https://beispiel.de"

    def test_optional_fields_omitted(self):
        obj = build_datenschutz_customer(_customer(phone=None, address=None, website=None))
        assert "phone" not in obj["contact"]
        assert "address" not in obj
        assert "website" not in obj

    def test_invite_default_true(self):
        assert build_datenschutz_customer(_customer())["invite_contact"] is True
        assert build_datenschutz_customer(_customer(), invite_contact=False)["invite_contact"] is False


# ------------------------------------------------------------------- Envelope

class TestEnvelope:
    def test_envelope_shape(self):
        cid = uuid.uuid4()
        env = build_envelope(cid, {"company_name": "X"})
        assert env["external_ref"] == str(cid)
        assert env["source"] == "celox-ops"
        assert uuid.UUID(env["handoff_id"])  # gültige uuid4
        assert env["sent_at"].endswith("Z")
        assert env["customer"] == {"company_name": "X"}

    def test_handoff_id_fresh_per_attempt(self):
        cid = uuid.uuid4()
        assert build_envelope(cid, {})["handoff_id"] != build_envelope(cid, {})["handoff_id"]

    def test_field_keys_flat_and_sorted(self):
        keys = field_keys({"company_name": "X", "contact": {"name": "M", "email": "e"}})
        assert keys == ["company_name", "contact.email", "contact.name"]


# -------------------------------------------------------------- Fehler-Mapping

class TestErrorMapping:
    def test_success_created(self):
        body = {"ok": True, "created": True, "company_id": 42}
        assert map_target_response(201, body) == body
        assert map_target_response(200, {"created": False}) == {"created": False}

    def test_409_is_fachkonflikt(self):
        with pytest.raises(HandoffError) as e:
            map_target_response(409, {"error": "conflict", "reason": "email_exists", "detail": "E-Mail vergeben"})
        assert e.value.status == 409
        assert e.value.code == "409"
        assert "email_exists" in e.value.detail

    def test_422_validation(self):
        with pytest.raises(HandoffError) as e:
            map_target_response(422, {"error": "validation", "fields": {"lead_email": "invalid"}})
        assert e.value.status == 422

    def test_401_maps_to_502(self):
        with pytest.raises(HandoffError) as e:
            map_target_response(401, {"error": "unauthorized"})
        assert e.value.status == 502
        assert "Key" in e.value.detail

    def test_503_not_configured(self):
        with pytest.raises(HandoffError) as e:
            map_target_response(503, {"error": "not_configured"})
        assert e.value.status == 503

    def test_5xx_is_temporary(self):
        with pytest.raises(HandoffError) as e:
            map_target_response(500, None)
        assert e.value.status == 502
        assert e.value.code == "500"
        assert "temporär" in e.value.detail
