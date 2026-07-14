"""Unit-Tests für die KI-Kostenberechnung (netzfrei, exakt aus usage)."""
from app.services.ai_pricing import Usage, compute_cost_usd, model_label


def test_compute_cost_sonnet():
    # 1M input @ $3 + 1M output @ $15 = $18
    assert compute_cost_usd("claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000) == 18.0
    # cache read viel günstiger
    assert compute_cost_usd("claude-sonnet-5", cache_read_tokens=1_000_000) == 0.30
    # Web-Suchen extra
    assert compute_cost_usd("claude-sonnet-5", web_searches=5) == round(5 * 0.01, 6)


def test_compute_cost_unknown_model_falls_back():
    assert compute_cost_usd("gibt-es-nicht", input_tokens=1_000_000) == 3.0  # → Default Sonnet


def test_usage_accumulates_from_dicts():
    u = Usage()
    u.add({"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 500,
           "cache_creation_input_tokens": 50,
           "server_tool_use": {"web_search_requests": 2}})
    u.add({"input_tokens": 100, "output_tokens": 30})
    assert u.input_tokens == 200 and u.output_tokens == 50
    assert u.cache_read_tokens == 500 and u.cache_write_tokens == 50 and u.web_searches == 2
    d = u.as_dict()
    assert d["web_searches"] == 2 and d["cache_read_tokens"] == 500


def test_usage_cost_uses_model():
    u = Usage()
    u.add({"input_tokens": 1_000_000})
    assert u.cost_usd("claude-haiku-4-5") == 1.0     # Haiku input $1/M


def test_usage_add_none_is_safe():
    u = Usage()
    u.add(None)
    assert u.input_tokens == 0


def test_model_label():
    assert model_label("claude-sonnet-5") == "Sonnet"
    assert model_label("unbekannt") == "unbekannt"
