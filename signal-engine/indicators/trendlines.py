"""
Trend Line Detection & Buy/Sell Zone Filter
=============================================
Implements the book-gold inner/outer trend line system:
- Inner: recent aggressive movement (fast)
- Outer: overall trend at ~45 degrees (moderate)
- Zone classification: BUY, SELL, CAUTIOUS, NEUTRAL
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators.structure import detect_swing_highs, detect_swing_lows


@dataclass(frozen=True)
class TrendLine:
    """A single trend line defined by slope and intercept."""
    slope: float
    intercept: float
    kind: str  # "support" | "resistance"


@dataclass(frozen=True)
class ZoneResult:
    zone: str  # "BUY" | "SELL" | "CAUTIOUS" | "NEUTRAL"
    inner_line: TrendLine | None
    outer_line: TrendLine | None


def _fit_line(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float] | None:
    """Simple linear regression. Returns (slope, intercept) or None."""
    if len(xs) < 2:
        return None
    # Remove NaN
    mask = ~(np.isnan(xs) | np.isnan(ys))
    xs, ys = xs[mask], ys[mask]
    if len(xs) < 2:
        return None
    coeffs = np.polyfit(xs, ys, 1)
    return float(coeffs[0]), float(coeffs[1])


def calculate_trend_lines(
    df: pd.DataFrame, window: int = 50
) -> ZoneResult:
    """Calculate inner and outer trend lines from swing points.

    Inner: last ~15 swing points (recent aggressive move).
    Outer: last ~30 swing points (overall trend).
    Support lines: connect swing lows (uptrend).
    Resistance lines: connect swing highs (downtrend).
    """
    if len(df) < window:
        return ZoneResult("NEUTRAL", None, None)

    recent = df.iloc[-window:]

    swing_h_mask = detect_swing_highs(recent, window=2)
    swing_l_mask = detect_swing_lows(recent, window=2)

    swing_highs = recent.loc[swing_h_mask]
    swing_lows = recent.loc[swing_l_mask]

    # --- Support trend line (from swing lows) ---
    support_line = None
    if len(swing_lows) >= 2:
        # Outer: all swing lows
        xs = np.arange(len(swing_lows), dtype=float)
        ys = swing_lows["low"].values.astype(float)
        result = _fit_line(xs, ys)
        if result:
            support_line = TrendLine(
                slope=result[0], intercept=result[1], kind="support"
            )

    # --- Resistance trend line (from swing highs) ---
    resistance_line = None
    if len(swing_highs) >= 2:
        xs = np.arange(len(swing_highs), dtype=float)
        ys = swing_highs["high"].values.astype(float)
        result = _fit_line(xs, ys)
        if result:
            resistance_line = TrendLine(
                slope=result[0], intercept=result[1], kind="resistance"
            )

    # If we couldn't build lines, neutral
    if support_line is None and resistance_line is None:
        return ZoneResult("NEUTRAL", None, None)

    # --- Determine zone from support line (primary) ---
    current_price = recent["close"].iloc[-1]

    # Evaluate support line at current position
    support_value = None
    if support_line is not None:
        # Extrapolate to the end of the data
        n_lows = len(swing_lows)
        support_value = support_line.slope * (n_lows - 1) + support_line.intercept

    resistance_value = None
    if resistance_line is not None:
        n_highs = len(swing_highs)
        resistance_value = resistance_line.slope * (n_highs - 1) + resistance_line.intercept

    # Zone determination
    # Uptrend: support line slopes up AND price above it
    if support_line is not None:
        if support_line.slope > 0:
            if support_value is not None and current_price > support_value:
                if resistance_value is None or current_price > resistance_value * 0.98:
                    return ZoneResult("BUY", support_line, resistance_line)
                else:
                    return ZoneResult("CAUTIOUS", support_line, resistance_line)

    # Downtrend: resistance line slopes down AND price below it
    if resistance_line is not None:
        if resistance_line.slope < 0:
            if resistance_value is not None and current_price < resistance_value:
                if support_value is None or current_price < support_value * 1.02:
                    return ZoneResult("SELL", support_line, resistance_line)
                else:
                    return ZoneResult("CAUTIOUS", support_line, resistance_line)

    return ZoneResult("NEUTRAL", support_line, resistance_line)


def check_zone_permission(direction: str, zone: str) -> bool:
    """Check if a trade direction is permitted in the current zone.

    - BUY signals allowed in BUY zone
    - SELL signals allowed in SELL zone
    - Both allowed in CAUTIOUS (reduced confidence)
    - Neither allowed in NEUTRAL (no clear trend)
    """
    if zone == "BUY":
        return direction == "BUY"
    elif zone == "SELL":
        return direction == "SELL"
    elif zone == "CAUTIOUS":
        return True  # allowed but strategies may apply penalty
    else:
        return False
