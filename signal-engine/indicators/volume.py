"""
Volume Absorption Detection
============================
Detects potential institutional absorption: high volume candle closing opposite to trend.
Example: high volume + bearish candle close near high = institutional buyers absorbing sells = bullish signal.

Works well for: BTC-USD, GC=F (gold), SI=F (silver)
Does NOT work for: USDJPY=X, GBPJPY=X (no reliable volume data from Yahoo Finance)
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def detect_volume_absorption(
    df: pd.DataFrame,
    volume_threshold: float = 2.0,
    lookback_bars: int = 20,
    check_bars: int = 3,
) -> dict[str, Any]:
    """Detect potential volume absorption in the last N bars.

    Args:
        df: OHLCV DataFrame with 'volume', 'open', 'high', 'low', 'close' columns
        volume_threshold: minimum volume ratio (current / average) to qualify as "high volume"
        lookback_bars: period for average volume calculation
        check_bars: how many recent bars to check for absorption patterns

    Returns:
        dict with:
        - absorption: list of detected absorption events
        - has_signal: bool
        - bullish_absorption: bool (high vol + bearish candle = buyers absorbing)
        - bearish_absorption: bool (high vol + bullish candle = sellers absorbing)
    """
    result: dict[str, Any] = {
        "absorption": [],
        "has_signal": False,
        "bullish_absorption": False,
        "bearish_absorption": False,
    }

    # Check if volume data exists
    if "volume" not in df.columns or df["volume"].isna().all():
        logger.debug("No volume data available — skipping absorption detection")
        return result

    if len(df) < lookback_bars + 1:
        return result

    avg_volume = df["volume"].rolling(window=lookback_bars).mean()
    avg_dollar_volume = (df["volume"] * df["close"]).rolling(window=lookback_bars).mean()

    for offset in range(check_bars):
        idx = -(offset + 1)  # -1, -2, -3 (most recent first)

        if idx < -len(df) + 1:
            continue

        bar = df.iloc[idx]
        avg_vol = avg_volume.iloc[idx]
        avg_dol = avg_dollar_volume.iloc[idx]

        if pd.isna(avg_vol) or avg_vol <= 0:
            continue

        vol_ratio = bar["volume"] / avg_vol
        dol_ratio = (bar["volume"] * bar["close"]) / avg_dol if avg_dol > 0 else 0

        # Only consider bars with significantly above-average volume
        if vol_ratio < volume_threshold:
            continue

        bar_body = bar["close"] - bar["open"]
        bar_range = bar["high"] - bar["low"]
        if bar_range <= 0:
            continue

        body_ratio = abs(bar_body) / bar_range

        # Bullish absorption: high volume + bearish candle (sellers tried, but price held)
        # Key: close is near the HIGH of the bar despite the bearish open
        is_bearish_candle = bar_body < 0
        close_near_high = (bar["close"] - bar["low"]) / bar_range > 0.6

        if is_bearish_candle and close_near_high:
            result["absorption"].append({
                "bar_offset": offset + 1,
                "direction": "bullish_absorption",
                "volume_ratio": round(vol_ratio, 2),
                "dollar_volume_ratio": round(dol_ratio, 2),
                "body_ratio": round(body_ratio, 2),
                "close": round(bar["close"], 5),
            })
            result["bullish_absorption"] = True

        # Bearish absorption: high volume + bullish candle (buyers tried, but price rejected)
        is_bullish_candle = bar_body > 0
        close_near_low = (bar["high"] - bar["close"]) / bar_range > 0.6

        if is_bullish_candle and close_near_low:
            result["absorption"].append({
                "bar_offset": offset + 1,
                "direction": "bearish_absorption",
                "volume_ratio": round(vol_ratio, 2),
                "dollar_volume_ratio": round(dol_ratio, 2),
                "body_ratio": round(body_ratio, 2),
                "close": round(bar["close"], 5),
            })
            result["bearish_absorption"] = True

    result["has_signal"] = len(result["absorption"]) > 0
    return result


def check_absorption_confluence(
    df: pd.DataFrame,
    direction: str,
    volume_threshold: float = 2.0,
) -> tuple[bool, str]:
    """Check if volume absorption confirms the signal direction.

    Returns (confirms: bool, reason: str).
    """
    result = detect_volume_absorption(df, volume_threshold=volume_threshold)

    if not result["has_signal"]:
        return False, ""

    if direction == "BUY" and result["bullish_absorption"]:
        top = result["absorption"][0]  # most recent
        return True, f"Volume absorption ({top['volume_ratio']}x avg) — bullish"

    if direction == "SELL" and result["bearish_absorption"]:
        top = result["absorption"][0]
        return True, f"Volume absorption ({top['volume_ratio']}x avg) — bearish"

    return False, ""
