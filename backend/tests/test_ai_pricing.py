"""Unit-Tests für die KI-Kostenberechnung + dynamische Preise (netzfrei)."""
import asyncio

import app.services.ai_pricing as P
from app.services.ai_pricing import (
    ModelPricing,
    Usage,
    compute_cost_usd,
    get_pricing,
    model_label,
    parse_pricing_table,
)


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
#  statische Kostenrechnung (Fallback-Konstanten)
# --------------------------------------------------------------------------- #
def test_compute_cost_sonnet():
    # Sonnet-5: 1M input @ $2 + 1M output @ $10 = $12
    assert compute_cost_usd("claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000) == 12.0
    assert compute_cost_usd("claude-sonnet-5", cache_read_tokens=1_000_000) == 0.20
    assert compute_cost_usd("claude-sonnet-5", web_searches=5) == round(5 * 0.01, 6)


def test_compute_cost_unknown_model_falls_back():
    assert compute_cost_usd("gibt-es-nicht", input_tokens=1_000_000) == 2.0  # → Default Sonnet


def test_usage_accumulates_and_costs():
    u = Usage()
    u.add({"input_tokens": 1_000_000, "server_tool_use": {"web_search_requests": 2}})
    assert u.input_tokens == 1_000_000 and u.web_searches == 2
    assert u.cost_usd("claude-haiku-4-5") == 1.0 + 2 * 0.01   # Haiku $1/M + 2 Web-Suchen


def test_usage_cost_with_explicit_pricing():
    u = Usage()
    u.add({"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    p = ModelPricing(2.0, 10.0, 2.5, 0.2, "S")
    assert u.cost_with(p) == 12.0


def test_model_label():
    assert model_label("claude-sonnet-5") == "Sonnet"
    assert model_label("unbekannt") == "unbekannt"


# --------------------------------------------------------------------------- #
#  dynamische Preise (LiteLLM-Tabelle)
# --------------------------------------------------------------------------- #
def test_parse_pricing_table():
    data = {
        "claude-sonnet-5": {"input_cost_per_token": 2e-06, "output_cost_per_token": 1e-05,
                            "cache_read_input_token_cost": 2e-07, "cache_creation_input_token_cost": 2.5e-06},
        "claude-haiku-4-5": {"input_cost_per_token": 1e-06, "output_cost_per_token": 5e-06},  # cache abgeleitet
        "irgendwas-fremdes": {"input_cost_per_token": 1e-06, "output_cost_per_token": 5e-06},
    }
    out = parse_pricing_table(data)
    assert out["claude-sonnet-5"].input == 2.0 and out["claude-sonnet-5"].output == 10.0
    assert out["claude-sonnet-5"].cache_read == 0.2
    assert out["claude-haiku-4-5"].cache_write == 1.25   # 1.25 × input abgeleitet
    assert "irgendwas-fremdes" not in out                 # nicht eins unserer Modelle


def test_parse_pricing_table_skips_implausible():
    data = {"claude-sonnet-5": {"input_cost_per_token": 999.0, "output_cost_per_token": 1e-05}}
    assert "claude-sonnet-5" not in parse_pricing_table(data)


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


class _Client:
    def __init__(self, payload=None, raise_exc=None):
        self.payload, self.raise_exc = payload, raise_exc

    async def get(self, url, timeout=None):
        if self.raise_exc:
            raise self.raise_exc
        return _Resp(self.payload)

    async def aclose(self):
        pass


def test_get_pricing_uses_dynamic():
    P._dyn.clear()
    P._fetched_at = 0.0
    client = _Client(payload={"claude-sonnet-5": {
        "input_cost_per_token": 2e-06, "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 2e-07}})
    p = _run(get_pricing("claude-sonnet-5", client))
    assert p.input == 2.0 and p.output == 10.0 and p.cache_read == 0.2


def test_get_pricing_falls_back_on_network_error():
    P._dyn.clear()
    P._fetched_at = 0.0
    client = _Client(raise_exc=RuntimeError("net down"))
    p = _run(get_pricing("claude-haiku-4-5", client))
    assert p.input == 1.0 and p.output == 5.0   # Fallback-Konstante
