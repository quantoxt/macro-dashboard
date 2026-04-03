"""
Consolidation Detector
======================
Detects trading ranges (tight/large) and breakouts from those ranges.
Built from book-gold.md rules.
"""

from dataclasses import dataclass

import pandas as pd

from indicators.technical import atr


@dataclass(frozen=True)
class ConsolidationResult:
    is_consolidating: bool
    range_type: str | None  # "tight" | "large" | None
    range_high: float
    range_low: float
    atr_declining: bool  # range tightening = pre-breakout signal


def detect_consolidation(
    df: pd.DataFrame,
    lookback: int = 20,
    tolerance_pips: float = 5.0,
    pip_size: float = 0.01,
    tight_range_pips: float = 60.0,
    large_range_pips: float = 300.0,
) -> ConsolidationResult:
    """Detect if price is consolidating in a range.

    Logic:
    - Check for equal-ish highs and lows in the lookback window
    - Classify range as tight (<60 pips), large (150-300+ pips), or normal
    - Check if ATR is declining (range tightening = pre-breakout)
    """
    if len(df) < lookback:
        return ConsolidationResult(
            is_consolidating=False,
            range_type=None,
            range_high=0.0,
            range_low=0.0,
            atr_declining=False,
        )

    recent = df.iloc[-lookback:]
    tolerance = tolerance_pips * pip_size

    range_high = recent["high"].max()
    range_low = recent["low"].min()
    range_size = range_high - range_low

    # Count how many highs cluster near the top of the range
    highs_near_top = sum(
        1 for h in recent["high"] if abs(h - range_high) <= tolerance * 3
    )
    # Count how many lows cluster near the bottom
    lows_near_bottom = sum(
        1 for l in recent["low"] if abs(l - range_low) <= tolerance * 3
    )

    # Need at least 2 touches on each side to call it a range
    has_range = highs_near_top >= 2 and lows_near_bottom >= 2

    # Check if range is tight (bodies mostly within a narrow band)
    body_range = (recent["close"] - recent["open"]).abs().mean()
    total_range = range_high - range_low
    narrow_bodies = body_range < total_range * 0.3 if total_range > 0 else False

    is_consolidating = has_range and narrow_bodies

    # Classify range type
    range_type = None
    range_pips = range_size / pip_size
    if is_consolidating:
        if range_pips < tight_range_pips:
            range_type = "tight"
        elif range_pips >= large_range_pips:
            range_type = "large"
        else:
            range_type = "tight"  # default medium ranges as tight for now

    # ATR declining check (range tightening)
    atr_series = atr(df, 14)
    atr_declining = False
    if len(atr_series.dropna()) >= 5:
        recent_atr = atr_series.dropna().iloc[-5:]
        atr_declining = recent_atr.iloc[-1] < recent_atr.iloc[0]

    return ConsolidationResult(
        is_consolidating=is_consolidating,
        range_type=range_type,
        range_high=range_high,
        range_low=range_low,
        atr_declining=atr_declining,
    )


def detect_breakout(
    df: pd.DataFrame,
    range_high: float,
    range_low: float,
) -> str | None:
    """Check if the latest candle breaks out of the range.

    Returns "BUY" if breakout above range_high, "SELL" if below range_low, None otherwise.
    Requires the candle to CLOSE beyond the range (not just wick).
    """
    if df.empty:
        return None

    last = df.iloc[-1]
    close = last["close"]

    if close > range_high:
        return "BUY"
    elif close < range_low:
        return "SELL"

    return None
