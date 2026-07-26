"""DB-freie Tests für die Tiefenanalyse (A2): PageSpeed-Parsing + KI-Review."""
import asyncio

from app.services.ai_pricing import Usage
from app.services.website_ai_review import (
    AI_DIMENSIONS,
    build_context,
    extract_text,
    ki_subscore,
    review_website,
)
from app.services.website_pagespeed import parse_pagespeed


# ---- PageSpeed-Parsing (rein) ----------------------------------------------
_LHR = {
    "lighthouseResult": {
        "configSettings": {"formFactor": "mobile"},
        "categories": {
            "performance": {"score": 0.42},
            "accessibility": {"score": 0.88},
            "best-practices": {"score": 1.0},
            "seo": {"score": 0.91},
        },
        "audits": {
            "largest-contentful-paint": {"score": 0.3, "displayValue": "4,1 s"},
            "cumulative-layout-shift": {"score": 0.95, "displayValue": "0,02"},
            "total-blocking-time": {"score": None, "displayValue": "310 ms"},
        },
    }
}


def test_parse_scores_scaled_to_0_100():
    out = parse_pagespeed(_LHR)
    assert out["scores"] == {"performance": 42, "accessibility": 88,
                             "best-practices": 100, "seo": 91}
    assert out["strategy"] == "mobile"


def test_parse_metrics_keep_display_values_and_none_score():
    out = parse_pagespeed(_LHR)
    by_label = {m["label"]: m for m in out["metrics"]}
    lcp = next(m for k, m in by_label.items() if k.startswith("LCP"))
    assert lcp["value"] == "4,1 s" and lcp["score"] == 30
    tbt = next(m for k, m in by_label.items() if k.startswith("TBT"))
    assert tbt["score"] is None and tbt["value"] == "310 ms"


def test_parse_missing_category_is_omitted_not_zero():
    out = parse_pagespeed({"lighthouseResult": {"categories": {"seo": {"score": 0.5}}}})
    assert out["scores"] == {"seo": 50}
    assert "performance" not in out["scores"]


def test_parse_empty_payload_is_safe():
    out = parse_pagespeed({})
    assert out["scores"] == {} and out["metrics"] == []


# ---- Text-Extraktion (rein) -------------------------------------------------
def test_extract_text_strips_scripts_styles_and_tags():
    html = """<html><head><style>.a{color:red}</style>
    <script>var x=1;</script></head><body><h1>Hallo &amp; Willkommen</h1>
    <p>Wir bauen Software.</p></body></html>"""
    txt = extract_text(html)
    assert "Hallo & Willkommen" in txt
    assert "Wir bauen Software." in txt
    assert "var x" not in txt and "color:red" not in txt


def test_extract_text_respects_limit():
    assert len(extract_text("<p>" + "x" * 9000 + "</p>", limit=100)) == 100


def test_extract_text_handles_empty():
    assert extract_text("") == ""


# ---- KI-Subscore (rein) -----------------------------------------------------
def test_ki_subscore_is_mean_and_clamped():
    review = {d: 80 for d in AI_DIMENSIONS}
    assert ki_subscore(review) == 80
    review["design"] = 150   # wird auf 100 geklemmt
    review["cta"] = -20      # auf 0
    assert 0 <= ki_subscore(review) <= 100


def test_ki_subscore_ignores_missing_dimensions():
    assert ki_subscore({"professionalitaet": 60, "vertrauen": 80}) == 70


def test_ki_subscore_empty_is_zero():
    assert ki_subscore({}) == 0


def test_build_context_contains_signals_and_url():
    ctx = build_context("https://x.de", "Seitentext",
                        {"has_impressum": True, "has_privacy": False,
                         "has_cookie_banner": False, "load_time_ms": 2500},
                        ["WordPress"])
    assert "https://x.de" in ctx and "Seitentext" in ctx
    assert "Impressum verlinkt: ja" in ctx
    assert "Datenschutzerklärung verlinkt: nein" in ctx
    assert "2.5s" in ctx and "WordPress" in ctx


# ---- review_website mit gefaktem Client ------------------------------------
class _Block:
    def __init__(self, payload):
        self.type = "tool_use"
        self.name = "review_website"
        self.input = payload


class _Usage:
    input_tokens = 500
    output_tokens = 200
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    server_tool_use = None


class _Msgs:
    def __init__(self, payload):
        self._p = payload
        self.captured = None

    async def create(self, **kw):
        self.captured = kw
        return type("R", (), {"usage": _Usage(), "content": [_Block(self._p)]})()


class _Client:
    def __init__(self, payload):
        self.messages = _Msgs(payload)


def test_review_website_maps_dimensions_and_score():
    payload = {d: 70 for d in AI_DIMENSIONS}
    payload.update({"summary": "Solider Auftritt.", "strengths": ["a", "b", "c", "d"],
                    "weaknesses": ["x"]})
    client = _Client(payload)
    usage = Usage()
    out = asyncio.run(review_website(client, "claude-sonnet-5", "https://x.de",
                                     "text", {"load_time_ms": 900}, ["WordPress"], usage))
    assert out["score"] == 70
    assert len(out["dimensions"]) == len(AI_DIMENSIONS)
    assert out["summary"] == "Solider Auftritt."
    assert len(out["strengths"]) == 3          # auf 3 gekappt
    assert out["version"]
    assert usage.input_tokens == 500 and usage.output_tokens == 200
    # erzwungene strukturierte Ausgabe
    assert client.messages.captured["tool_choice"]["name"] == "review_website"
