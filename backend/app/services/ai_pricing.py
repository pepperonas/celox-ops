"""Preise & exakte Kostenberechnung für die KI-Lead-Suche (Anthropic API).

Preise in **USD pro 1 Mio Token** (bzw. pro Web-Suche). Zentral hier pflegbar —
bitte gelegentlich gegen das aktuelle Anthropic-Pricing gegenprüfen. Die Kosten
werden NICHT geschätzt, sondern aus der `usage`-Antwort der API berechnet.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input: float          # $/Mio Input-Token
    output: float         # $/Mio Output-Token
    cache_write: float    # $/Mio Cache-Schreib-Token (5-min-Cache)
    cache_read: float     # $/Mio Cache-Lese-Token
    label: str


AI_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-5":  ModelPricing(3.0, 15.0, 3.75, 0.30, "Sonnet"),
    "claude-haiku-4-5": ModelPricing(1.0, 5.0, 1.25, 0.10, "Haiku"),
    "claude-opus-4-8":  ModelPricing(15.0, 75.0, 18.75, 1.50, "Opus"),
}
WEB_SEARCH_USD = 0.01        # ≈ $10 / 1.000 Web-Suchen
DEFAULT_MODEL = "claude-sonnet-5"
ALLOWED_MODELS = tuple(AI_PRICING.keys())


def model_label(model: str) -> str:
    p = AI_PRICING.get(model)
    return p.label if p else model


def compute_cost_usd(model: str, *, input_tokens: int = 0, output_tokens: int = 0,
                     cache_write_tokens: int = 0, cache_read_tokens: int = 0,
                     web_searches: int = 0) -> float:
    """Exakte USD-Kosten aus den Token-Typen + Web-Suchen."""
    p = AI_PRICING.get(model) or AI_PRICING[DEFAULT_MODEL]
    token_usd = (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_write_tokens * p.cache_write
        + cache_read_tokens * p.cache_read
    ) / 1_000_000
    return round(token_usd + web_searches * WEB_SEARCH_USD, 6)


class Usage:
    """Akkumuliert die Token-/Such-Zähler über mehrere API-Calls eines Laufs."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_write_tokens = 0
        self.cache_read_tokens = 0
        self.web_searches = 0

    def add(self, api_usage) -> None:
        """Nimmt ein Anthropic-`usage`-Objekt ODER ein dict und addiert es."""
        def g(k):
            if api_usage is None:
                return 0
            v = api_usage.get(k) if isinstance(api_usage, dict) else getattr(api_usage, k, 0)
            return int(v or 0)
        self.input_tokens += g("input_tokens")
        self.output_tokens += g("output_tokens")
        self.cache_write_tokens += g("cache_creation_input_tokens")
        self.cache_read_tokens += g("cache_read_input_tokens")
        # Server-Tool-Nutzung (Web-Suche): usage.server_tool_use.web_search_requests
        stu = api_usage.get("server_tool_use") if isinstance(api_usage, dict) else getattr(api_usage, "server_tool_use", None)
        if stu is not None:
            self.web_searches += int((stu.get("web_search_requests") if isinstance(stu, dict)
                                      else getattr(stu, "web_search_requests", 0)) or 0)

    def cost_usd(self, model: str) -> float:
        return compute_cost_usd(
            model, input_tokens=self.input_tokens, output_tokens=self.output_tokens,
            cache_write_tokens=self.cache_write_tokens, cache_read_tokens=self.cache_read_tokens,
            web_searches=self.web_searches)

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cache_write_tokens": self.cache_write_tokens, "cache_read_tokens": self.cache_read_tokens,
            "web_searches": self.web_searches,
        }
