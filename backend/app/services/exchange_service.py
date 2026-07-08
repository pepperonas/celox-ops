"""Live USD→EUR exchange rate with caching and safe fallbacks.

Source: Frankfurter API (ECB reference rates, free, no API key,
https://api.frankfurter.dev). The rate is cached in-memory for 12 h
(ECB publishes once per working day). On fetch failure the last
successfully fetched rate is reused indefinitely; if none exists yet,
the hardcoded FALLBACK_USD_EUR applies — so invoice generation never
blocks or fails on a network hiccup.
"""
import time

import httpx

FALLBACK_USD_EUR = 0.92
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR"
_TTL_SECONDS = 12 * 3600

# Module-level cache: {rate, date, fetched_at (monotonic), source}
_cache: dict = {"rate": None, "date": None, "fetched_at": 0.0, "source": "fallback"}


def parse_frankfurter(payload) -> float | None:
    """Extract the EUR rate from a Frankfurter response; None if implausible.
    Plausibility bounds (0.5–1.5) guard against a broken upstream feeding a
    wildly wrong factor into invoices."""
    try:
        rate = float(payload["rates"]["EUR"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0.5 <= rate <= 1.5):
        return None
    return rate


def _is_fresh() -> bool:
    return _cache["rate"] is not None and (time.monotonic() - _cache["fetched_at"]) < _TTL_SECONDS


async def get_rate_info() -> dict:
    """Return {rate, source, date}. source: 'ecb' (fresh or last-known-good)
    or 'fallback' (hardcoded constant)."""
    if not _is_fresh():
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(FRANKFURTER_URL)
            if resp.status_code == 200:
                rate = parse_frankfurter(resp.json())
                if rate is not None:
                    _cache.update(
                        rate=rate,
                        date=resp.json().get("date"),
                        fetched_at=time.monotonic(),
                        source="ecb",
                    )
        except Exception:
            pass  # keep last-known-good / fallback

    if _cache["rate"] is not None:
        return {"rate": _cache["rate"], "source": _cache["source"], "date": _cache["date"]}
    return {"rate": FALLBACK_USD_EUR, "source": "fallback", "date": None}


async def get_usd_eur_rate() -> float:
    return (await get_rate_info())["rate"]
