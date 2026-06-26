"""Unit tests for the legal-compliance engine — pure logic, no DB required.
Run via: cd backend && pytest -v tests/test_compliance.py
"""
import os
import uuid
from datetime import date
from types import SimpleNamespace

# Set required env BEFORE importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

from app.routers.compliance import _build_items  # noqa: E402
from app.routers.documents import COMPLIANCE_REQUIRED_DEFAULTS  # noqa: E402


def _tpl(name="AGB", category="allgemein"):
    return SimpleNamespace(id=uuid.uuid4(), name=name, category=category)


def _rec(signed_at=None, method=None, attachment_id=None, note=None):
    return SimpleNamespace(
        signed_at=signed_at, method=method, attachment_id=attachment_id, note=note
    )


def test_no_record_means_unsigned():
    t = _tpl()
    items = _build_items([t], {})
    assert len(items) == 1
    assert items[0].signed is False
    assert items[0].signed_at is None
    assert items[0].attachment_id is None


def test_record_with_signed_at_is_signed():
    t = _tpl(name="Auftragsverarbeitungsvertrag (AV-Vertrag)", category="datenschutz")
    aid = uuid.uuid4()
    rec = _rec(signed_at=date(2026, 6, 1), method="upload", attachment_id=aid, note="ok")
    items = _build_items([t], {t.id: rec})
    item = items[0]
    assert item.signed is True
    assert item.signed_at == date(2026, 6, 1)
    assert item.method == "upload"
    assert item.attachment_id == str(aid)
    assert item.name == "Auftragsverarbeitungsvertrag (AV-Vertrag)"
    assert item.category == "datenschutz"


def test_record_without_signed_at_is_unsigned():
    # A record can exist (e.g. created then reset) but count as not fulfilled.
    t = _tpl()
    rec = _rec(signed_at=None, method="manual")
    items = _build_items([t], {t.id: rec})
    assert items[0].signed is False


def test_manual_record_has_no_attachment():
    t = _tpl()
    rec = _rec(signed_at=date(2026, 6, 2), method="manual", attachment_id=None)
    items = _build_items([t], {t.id: rec})
    assert items[0].signed is True
    assert items[0].method == "manual"
    assert items[0].attachment_id is None


def test_preserves_template_order_and_mixed_status():
    t1, t2, t3 = _tpl(name="AGB"), _tpl(name="AVV"), _tpl(name="NDA")
    records = {t2.id: _rec(signed_at=date(2026, 6, 3))}
    items = _build_items([t1, t2, t3], records)
    assert [i.name for i in items] == ["AGB", "AVV", "NDA"]
    assert [i.signed for i in items] == [False, True, False]


def test_compliance_required_defaults_are_agb_and_avv():
    assert COMPLIANCE_REQUIRED_DEFAULTS == {
        "Allgemeine Geschäftsbedingungen (AGB)",
        "Auftragsverarbeitungsvertrag (AV-Vertrag)",
    }
