"""DB-freie Tests für den KI-Mailentwurf (services/lead_email_ai.py)."""
import asyncio
from types import SimpleNamespace

from app.services.ai_pricing import Usage
from app.services.lead_email_ai import build_lead_context, draft_lead_email


def _lead(**over):
    base = dict(
        company="Beispiel GmbH", contact_name=None, role=None, decision_maker=None,
        target=None, employee_count=None, website=None, tags=None, notes=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestBuildLeadContext:
    def test_only_present_fields(self):
        ctx = build_lead_context(_lead(company="A2 Doku GmbH", target="bcs / zeiterfassung"))
        assert "Firma: A2 Doku GmbH" in ctx
        assert "Target (Verkaufs-Winkel/Pain): bcs / zeiterfassung" in ctx
        # leere Felder tauchen NICHT auf (kein "Ansprechpartner:" ohne Wert)
        assert "Ansprechpartner:" not in ctx
        assert "Website:" not in ctx

    def test_all_fields(self):
        ctx = build_lead_context(_lead(
            company="X GmbH", contact_name="Max Muster", role="Geschäftsführung",
            decision_maker="Erika Chefin", target="IT-Sicherheit / ISO 27001",
            employee_count=120, website="https://x.de",
            tags=["Automotive", "Softwareentwicklung"], notes="Kontext hier",
        ))
        for frag in ["X GmbH", "Max Muster", "Geschäftsführung", "Erika Chefin",
                     "ISO 27001", "120", "https://x.de", "Automotive, Softwareentwicklung",
                     "Kontext hier"]:
            assert frag in ctx, frag

    def test_notes_truncated(self):
        ctx = build_lead_context(_lead(notes="x" * 1000))
        assert "x" * 600 in ctx
        assert "x" * 601 not in ctx

    def test_empty_lead_has_fallback(self):
        assert "keine strukturierten Angaben" in build_lead_context(_lead(company=None))


class _FakeUsageBlock:
    input_tokens = 300
    output_tokens = 150
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _FakeToolBlock:
    type = "tool_use"
    name = "draft_email"

    def __init__(self, payload):
        self.input = payload


class _FakeResp:
    def __init__(self, payload):
        self.usage = _FakeUsageBlock()
        self.content = [_FakeToolBlock(payload)]


class _FakeMessages:
    def __init__(self, payload):
        self._payload = payload
        self.captured = None

    async def create(self, **kwargs):
        self.captured = kwargs
        return _FakeResp(self._payload)


class _FakeClient:
    def __init__(self, payload):
        self.messages = _FakeMessages(payload)


class TestDraftLeadEmail:
    def _run(self, payload, lead):
        client = _FakeClient(payload)
        usage = Usage()
        result = asyncio.run(draft_lead_email(client, "claude-sonnet-5", lead, usage))
        return result, client, usage

    def test_returns_subject_body_product(self):
        payload = {"subject": "Zeiterfassung, die passt", "body": "Sehr geehrte…\nMfG",
                   "product": "BCS-Einführung"}
        result, _, _ = self._run(payload, _lead(target="bcs / zeiterfassung"))
        assert result["subject"] == "Zeiterfassung, die passt"
        assert result["body"].startswith("Sehr geehrte")
        assert result["product"] == "BCS-Einführung"

    def test_missing_product_is_none(self):
        result, _, _ = self._run({"subject": "S", "body": "B"}, _lead())
        assert result["product"] is None

    def test_strips_whitespace_and_appends_signature(self):
        from app.services.lead_email_ai import SIGNATURE
        result, _, _ = self._run({"subject": "  S  ", "body": "  B  "}, _lead())
        assert result["subject"] == "S"
        assert result["body"].startswith("B")
        assert result["body"].endswith(SIGNATURE)
        assert "martin.pfeffer@celox.io" in result["body"]

    def test_signature_not_duplicated(self):
        from app.services.lead_email_ai import SIGNATURE
        result, _, _ = self._run({"subject": "S", "body": f"Text\n\n{SIGNATURE}"}, _lead())
        assert result["body"].count("Martin Pfeffer") == 1

    def test_lead_context_reaches_the_prompt(self):
        # Sicherheitsnetz: die Firma/Target müssen im User-Prompt landen
        _, client, _ = self._run({"subject": "S", "body": "B"},
                                 _lead(company="Peak GmbH", target="bcs / zeiterfassung"))
        user_msg = client.messages.captured["messages"][0]["content"]
        assert "Peak GmbH" in user_msg
        assert "bcs / zeiterfassung" in user_msg
        # erzwungene strukturierte Ausgabe
        assert client.messages.captured["tool_choice"]["name"] == "draft_email"

    def test_usage_is_accumulated(self):
        _, _, usage = self._run({"subject": "S", "body": "B"}, _lead())
        assert usage.input_tokens == 300 and usage.output_tokens == 150
