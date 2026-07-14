"""Preise & exakte Kostenberechnung für die KI-Lead-Suche (Anthropic API).

Preise in **USD pro 1 Mio Token** (bzw. pro Web-Suche). Anthropic hat KEINE
öffentliche Preis-API — daher werden die Preise **dynamisch aus der gepflegten
LiteLLM-Preistabelle** nachgeladen (enthält die exakten Anthropic-Modell-IDs,
wird bei Preisänderungen aktualisiert), mit 12-h-Cache, Plausibilitätsprüfung
und **Fallback auf die Konstanten unten** (Stand geprüft 2026-07). So sind die
Kosten immer korrekt, ohne je zu brechen.
"""
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ModelPricing:
    input: float          # $/Mio Input-Token
    output: float         # $/Mio Output-Token
    cache_write: float    # $/Mio Cache-Schreib-Token (5-min-Cache)
    cache_read: float     # $/Mio Cache-Lese-Token
    label: str


# Fallback-Konstanten (aktuell verifiziert gegen die Anthropic-Preise).
AI_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-5":  ModelPricing(2.0, 10.0, 2.5, 0.20, "Sonnet"),
    "claude-haiku-4-5": ModelPricing(1.0, 5.0, 1.25, 0.10, "Haiku"),
    "claude-opus-4-8":  ModelPricing(5.0, 25.0, 6.25, 0.50, "Opus"),
}
WEB_SEARCH_USD = 0.01        # ≈ $10 / 1.000 Web-Suchen
DEFAULT_MODEL = "claude-sonnet-5"
ALLOWED_MODELS = tuple(AI_PRICING.keys())

# ---- dynamische Preise ----------------------------------------------------- #
_PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
_PRICING_TTL = 12 * 3600
_dyn: dict[str, ModelPricing] = {}    # last-known-good aus dem Netz
_fetched_at: float = 0.0


def model_label(model: str) -> str:
    p = _dyn.get(model) or AI_PRICING.get(model)
    return p.label if p else model


def _plausible(p: ModelPricing) -> bool:
    return 0.05 <= p.input <= 200 and 0.05 <= p.output <= 2000 and p.output >= p.input


def parse_pricing_table(data: dict) -> dict[str, ModelPricing]:
    """LiteLLM-JSON → {model: ModelPricing} nur für unsere Modelle (netzfrei testbar)."""
    out: dict[str, ModelPricing] = {}
    for model, base in AI_PRICING.items():
        e = data.get(model)
        if not isinstance(e, dict):
            continue
        try:
            inp = float(e["input_cost_per_token"]) * 1e6
            outp = float(e["output_cost_per_token"]) * 1e6
        except (KeyError, TypeError, ValueError):
            continue
        cw = (float(e["cache_creation_input_token_cost"]) * 1e6
              if e.get("cache_creation_input_token_cost") else round(inp * 1.25, 4))
        cr = (float(e["cache_read_input_token_cost"]) * 1e6
              if e.get("cache_read_input_token_cost") else round(inp * 0.10, 4))
        p = ModelPricing(round(inp, 4), round(outp, 4), round(cw, 4), round(cr, 4), base.label)
        if _plausible(p):
            out[model] = p
    return out


async def refresh_pricing(client: httpx.AsyncClient | None = None) -> dict[str, ModelPricing]:
    """Holt die Preistabelle (LiteLLM) und aktualisiert den Cache. Fehler werfen
    NICHT nach außen bei get_pricing — hier für den Aufrufer/Test aber sichtbar."""
    global _fetched_at
    close = client is None
    client = client or httpx.AsyncClient()
    try:
        resp = await client.get(_PRICING_URL, timeout=15)
        resp.raise_for_status()
        fetched = parse_pricing_table(resp.json())
    finally:
        if close:
            await client.aclose()
    if fetched:
        _dyn.update(fetched)
        _fetched_at = time.monotonic()
    return fetched


async def get_pricing(model: str, client: httpx.AsyncClient | None = None) -> ModelPricing:
    """Aktueller Preis: dynamisch (12-h-Cache) mit Fallback auf die Konstanten.
    Wirft nie — im Zweifel Konstanten."""
    if not _dyn or (time.monotonic() - _fetched_at) > _PRICING_TTL:
        try:
            await refresh_pricing(client)
        except Exception:  # noqa: BLE001 — Preis-Fetch darf nie den Lauf kippen
            pass
    return _dyn.get(model) or AI_PRICING.get(model) or AI_PRICING[DEFAULT_MODEL]


def pricing_source() -> str:
    return "live" if _dyn else "fallback"


# ---- Kostenberechnung ------------------------------------------------------ #
def compute_cost_from(p: ModelPricing, *, input_tokens: int = 0, output_tokens: int = 0,
                      cache_write_tokens: int = 0, cache_read_tokens: int = 0,
                      web_searches: int = 0) -> float:
    token_usd = (
        input_tokens * p.input + output_tokens * p.output
        + cache_write_tokens * p.cache_write + cache_read_tokens * p.cache_read
    ) / 1_000_000
    return round(token_usd + web_searches * WEB_SEARCH_USD, 6)


def compute_cost_usd(model: str, **kw) -> float:
    """Kosten mit den (statischen) Konstanten — für Tests/Fallback."""
    return compute_cost_from(AI_PRICING.get(model) or AI_PRICING[DEFAULT_MODEL], **kw)


class Usage:
    """Akkumuliert die Token-/Such-Zähler über mehrere API-Calls eines Laufs."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_write_tokens = 0
        self.cache_read_tokens = 0
        self.web_searches = 0

    def add(self, api_usage) -> None:
        def g(k):
            if api_usage is None:
                return 0
            v = api_usage.get(k) if isinstance(api_usage, dict) else getattr(api_usage, k, 0)
            return int(v or 0)
        self.input_tokens += g("input_tokens")
        self.output_tokens += g("output_tokens")
        self.cache_write_tokens += g("cache_creation_input_tokens")
        self.cache_read_tokens += g("cache_read_input_tokens")
        stu = api_usage.get("server_tool_use") if isinstance(api_usage, dict) else getattr(api_usage, "server_tool_use", None)
        if stu is not None:
            self.web_searches += int((stu.get("web_search_requests") if isinstance(stu, dict)
                                      else getattr(stu, "web_search_requests", 0)) or 0)

    def cost_usd(self, model: str) -> float:
        """Kosten mit statischen Konstanten (Fallback/Tests)."""
        return compute_cost_usd(model, **self.as_dict())

    def cost_with(self, pricing: ModelPricing) -> float:
        """Kosten mit einem konkreten (ggf. dynamisch geladenen) Preis."""
        return compute_cost_from(pricing, **self.as_dict())

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cache_write_tokens": self.cache_write_tokens, "cache_read_tokens": self.cache_read_tokens,
            "web_searches": self.web_searches,
        }
