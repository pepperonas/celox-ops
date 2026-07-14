"""Unit-Tests für die KI-Lead-Orchestrierung (netzfrei, gemockter Anthropic-Client
+ gemockte discover/verify). Kein echtes SDK/Netz nötig."""
import asyncio

import app.services.ai_lead_agent as agent
from app.services.ai_lead_agent import (
    DiscoveryCaps,
    gather_candidates,
    parse_brief,
    rank_candidates,
)
from app.services.ai_pricing import Usage
from app.services.email_verifier import EmailCheck, EmailStatus


def _run(coro):
    return asyncio.run(coro)


# ---- Fake Anthropic-Client ------------------------------------------------ #
class _Block:
    def __init__(self, name, inp):
        self.type, self.name, self.input = "tool_use", name, inp


class _Resp:
    def __init__(self, block):
        self.content = [block]
        self.usage = {"input_tokens": 120, "output_tokens": 40}


class _Msgs:
    def __init__(self, mapping):
        self.mapping = mapping

    async def create(self, **kw):
        name = kw["tool_choice"]["name"]
        return _Resp(_Block(name, self.mapping[name]))


class _AI:
    def __init__(self, mapping):
        self.messages = _Msgs(mapping)


# ---- parse_brief ---------------------------------------------------------- #
def test_parse_brief_returns_params_and_defaults():
    ai = _AI({"search_params": {"segments": ["hausverwaltung"], "cities": ["Berlin"]}})
    u = Usage()
    p = _run(parse_brief(ai, "claude-sonnet-5", "10 Hausverwaltungen Berlin", u))
    assert p["segments"] == ["hausverwaltung"] and p["cities"] == ["Berlin"]
    assert p["count"] == 10 and p["fit_criteria"] == "" and p["exclude"] == ""
    assert u.input_tokens == 120  # usage getrackt


# ---- rank_candidates ------------------------------------------------------ #
def test_rank_selects_by_index_and_caps_to_count():
    ai = _AI({"ranked": {"selected": [
        {"index": 1, "fit_reason": "klein & unabhängig"},
        {"index": 0, "fit_reason": "ok"},
    ]}})
    cands = [{"name": "A"}, {"name": "B"}]
    r = _run(rank_candidates(ai, "m", "brief", {"count": 1}, cands, Usage()))
    assert len(r) == 1 and r[0]["name"] == "B" and r[0]["fit_reason"] == "klein & unabhängig"


def test_rank_ignores_out_of_range_index():
    ai = _AI({"ranked": {"selected": [{"index": 9, "fit_reason": "x"}, {"index": 0, "fit_reason": "y"}]}})
    r = _run(rank_candidates(ai, "m", "b", {"count": 10}, [{"name": "A"}], Usage()))
    assert [c["name"] for c in r] == ["A"]


def test_rank_empty_candidates():
    assert _run(rank_candidates(_AI({}), "m", "b", {"count": 5}, [], Usage())) == []


# ---- gather_candidates ---------------------------------------------------- #
def test_gather_dedups_and_keeps_only_deliverable(monkeypatch):
    async def fake_discover(seg, city, limit, client):
        return [
            {"name": "X", "website": "https://x.de", "email": "a@x.de"},
            {"name": "X-dup", "website": "https://www.x.de/", "email": "a@x.de"},  # gleiche Domain → dedup
            {"name": "Y", "website": "https://y.de", "email": "b@y.de"},           # no_mx → raus
        ]

    async def fake_verify(email, mx_cache=None):
        return EmailCheck(status=EmailStatus.VALID if "x.de" in email else EmailStatus.NO_MX)

    monkeypatch.setattr(agent, "discover_osm", fake_discover)
    monkeypatch.setattr(agent, "verify_email", fake_verify)
    res = _run(gather_candidates({"segments": ["hausverwaltung"], "cities": ["Berlin"]},
                                 None, DiscoveryCaps(), []))
    assert [c["name"] for c in res] == ["X"]
    assert res[0]["email_status"] == "valid"


def test_gather_handles_overpass_error(monkeypatch):
    async def boom(seg, city, limit, client):
        raise ValueError("Overpass überlastet")
    monkeypatch.setattr(agent, "discover_osm", boom)
    notes: list[str] = []
    res = _run(gather_candidates({"segments": ["hausverwaltung"], "cities": ["Berlin"]},
                                 None, DiscoveryCaps(), notes))
    assert res == [] and notes and "Overpass" in notes[0]
