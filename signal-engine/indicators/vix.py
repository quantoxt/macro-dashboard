"""
VIX Regime Filter
==================
Fetches VIX (CBOE Volatility Index) and compares to its SMA.
When VIX > SMA, market is in high-fear regime — signals should be paused or de-prioritized.

Data source: Yahoo Finance (^VIX ticker)
Cache: module-level with 1-hour TTL (VIX updates intraday but doesn't change dramatically)
"""

import logging
import time

import yfinance as yf

logger = logging.getLogger(__name__)

# Module-level cache
_vix_cache: dict = {"value": None, "sma": None, "fetched_at": 0.0}
_VIX_CACHE_TTL: int = 3600  # 1 hour


async def fetch_vix() -> float | None:
    """Fetch current VIX value from Yahoo Finance.

    Returns VIX close price or None on failure.
    Never raises — returns None on any error.
    """
    global _vix_cache

    # Check cache
    if _vix_cache["value"] is not None and (time.time() - _vix_cache["fetched_at"]) < _VIX_CACHE_TTL:
        return _vix_cache["value"]

    try:
        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="5d")
        if hist.empty:
            logger.warning("VIX: no data returned from Yahoo Finance")
            return _vix_cache["value"]  # return stale if available

        vix_value = float(hist["Close"].iloc[-1])
        _vix_cache["value"] = vix_value
        _vix_cache["fetched_at"] = time.time()
        logger.debug("VIX fetched: %.2f", vix_value)
        return vix_value

    except Exception as exc:
        logger.warning("VIX fetch failed: %s", exc)
        return _vix_cache["value"]  # return stale if available


async def fetch_vix_with_sma(sma_period: int = 20) -> dict:
    """Fetch VIX value and its SMA for regime comparison.

    Returns dict with:
    - vix: current VIX value
    - sma: VIX SMA value
    - regime: "normal" | "high_fear" | "unknown"
    - description: human-readable regime description
    """
    global _vix_cache

    # Check cache
    if (_vix_cache["value"] is not None and _vix_cache["sma"] is not None
            and (time.time() - _vix_cache["fetched_at"]) < _VIX_CACHE_TTL):
        vix_val = _vix_cache["value"]
        sma_val = _vix_cache["sma"]
    else:
        try:
            ticker = yf.Ticker("^VIX")
            # Fetch enough history for SMA calculation
            hist = ticker.history(period="1mo")
            if hist.empty:
                logger.warning("VIX+SMA: no data returned")
                return {"vix": None, "sma": None, "regime": "unknown", "description": "VIX data unavailable"}

            close = hist["Close"]
            sma_val = float(close.rolling(window=sma_period).mean().iloc[-1])
            vix_val = float(close.iloc[-1])

            _vix_cache["value"] = vix_val
            _vix_cache["sma"] = sma_val
            _vix_cache["fetched_at"] = time.time()
            logger.debug("VIX: %.2f, SMA(%d): %.2f", vix_val, sma_period, sma_val)

        except Exception as exc:
            logger.warning("VIX+SMA fetch failed: %s", exc)
            vix_val = _vix_cache["value"]
            sma_val = _vix_cache["sma"]

    if vix_val is None or sma_val is None:
        return {"vix": vix_val, "sma": sma_val, "regime": "unknown", "description": "VIX data unavailable"}

    high_fear = vix_val > sma_val
    regime = "high_fear" if high_fear else "normal"

    if high_fear:
        description = f"High fear regime (VIX {vix_val:.1f} > SMA {sma_val:.1f})"
    else:
        description = f"Normal regime (VIX {vix_val:.1f} < SMA {sma_val:.1f})"

    return {
        "vix": round(vix_val, 2),
        "sma": round(sma_val, 2),
        "regime": regime,
        "description": description,
    }


def get_vix_cache_status() -> dict:
    """Return VIX cache status for diagnostics."""
    age = time.time() - _vix_cache["fetched_at"] if _vix_cache["fetched_at"] else 0
    return {
        "cached": _vix_cache["value"] is not None,
        "vix": _vix_cache["value"],
        "sma": _vix_cache["sma"],
        "age_seconds": round(age),
        "ttl_seconds": _VIX_CACHE_TTL,
        "fresh": age < _VIX_CACHE_TTL,
    }
