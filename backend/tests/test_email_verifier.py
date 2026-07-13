"""Unit-Tests für die SMTP-freie E-Mail-Qualitätsprüfung (netzfrei):
Syntax/Normalisierung/Disposable/Rolle rein; MX über einen injizierten Resolver."""
import asyncio

from app.services.email_verifier import (
    EmailStatus,
    MxUnknown,
    classify_syntax,
    verify_email,
)


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
#  classify_syntax (rein)
# --------------------------------------------------------------------------- #
def test_syntax_valid_and_normalized():
    s = classify_syntax("  Max@Firma.DE ")
    assert s.ok and s.domain == "firma.de" and s.local == "max"
    assert not s.is_role and not s.is_disposable


def test_syntax_invalid():
    assert classify_syntax("kein-email").ok is False
    assert classify_syntax("").ok is False
    assert classify_syntax(None).ok is False


def test_syntax_role_and_disposable_flags():
    assert classify_syntax("info@firma.de").is_role is True
    assert classify_syntax("kontakt@firma.de").is_role is True
    assert classify_syntax("max@mailinator.com").is_disposable is True


# --------------------------------------------------------------------------- #
#  verify_email (MX-Resolver injiziert)
# --------------------------------------------------------------------------- #
def _resolver(result):
    async def _r(domain):
        if isinstance(result, Exception):
            raise result
        return result
    return _r


def test_verify_valid_with_mx():
    r = _run(verify_email("max@firma.de", resolve=_resolver(["mx.firma.de"])))
    assert r.status == EmailStatus.VALID and r.mx_host == "mx.firma.de"


def test_verify_role_with_mx():
    r = _run(verify_email("info@firma.de", resolve=_resolver(["mx.firma.de"])))
    assert r.status == EmailStatus.ROLE and r.is_role


def test_verify_no_mx():
    r = _run(verify_email("max@firma.de", resolve=_resolver([])))
    assert r.status == EmailStatus.NO_MX


def test_verify_unknown_on_transient_dns():
    r = _run(verify_email("max@firma.de", resolve=_resolver(MxUnknown("timeout"))))
    assert r.status == EmailStatus.UNKNOWN


def test_verify_disposable_skips_dns():
    called = {"n": 0}

    async def _r(domain):
        called["n"] += 1
        return ["mx"]

    r = _run(verify_email("x@mailinator.com", resolve=_r))
    assert r.status == EmailStatus.DISPOSABLE and called["n"] == 0   # kein DNS bei Wegwerf


def test_verify_invalid_syntax():
    r = _run(verify_email("nope", resolve=_resolver(["mx"])))
    assert r.status == EmailStatus.INVALID_SYNTAX


def test_verify_uses_mx_cache():
    calls = {"n": 0}

    async def _r(domain):
        calls["n"] += 1
        return ["mx.firma.de"]

    cache: dict = {}
    _run(verify_email("a@firma.de", resolve=_r, mx_cache=cache))
    _run(verify_email("b@firma.de", resolve=_r, mx_cache=cache))
    assert calls["n"] == 1 and cache["firma.de"] == ["mx.firma.de"]   # zweiter Treffer aus Cache
