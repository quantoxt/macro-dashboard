"""
Fibonacci A-B-C-D Framework
=============================
Implements the book-gold Fib retracement → extension mapping:
  - Bounce at 0.382 → target 1.618 extension
  - Bounce at 0.50   → target 1.618
  - Bounce at 0.618  → target 1.618 (may hit 1.27 first)
  - Bounce at 0.786  → target 1.27 only
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from indicators.structure import SRLevel, detect_swing_highs, detect_swing_lows


# Mapping: retracement level → target extension level
RETRACEMENT_TO_EXTENSION = {
    0.382: 1.618,
    0.500: 1.618,
    0.618: 1.618,
    0.786: 1.270,
}


@dataclass(frozen=True)
class ABCDResult:
    """Result of A-B-C-D swing identification."""
    swing_a: float  # Start of the move
    swing_b: float  # End of the move (peak/trough)
    swing_c: float  # Retracement level (bounce point)
    retracement: float  # Which Fib level C bounced at (0.382, 0.50, 0.618, 0.786)
    extension_target: float  # D extension target price
    extension_ratio: float  # D extension ratio used


def fib_retracement_levels(swing_high: float, swing_low: float) -> dict[str, float]:
    """Calculate Fib retracement levels between swing high and low."""
    diff = swing_high - swing_low
    return {
        "0.0": swing_high,
        "0.236": swing_high - 0.236 * diff,
        "0.382": swing_high - 0.382 * diff,
        "0.500": swing_high - 0.500 * diff,
        "0.618": swing_high - 0.618 * diff,
        "0.786": swing_high - 0.786 * diff,
        "1.0": swing_low,
    }


def fib_extension_levels(
    swing_a: float, swing_b: float, direction: str = "up"
) -> dict[str, float]:
    """Calculate Fib extension levels from A-B swing.

    direction='up': A is low, B is high, extensions go above B.
    direction='down': A is high, B is low, extensions go below B.
    """
    diff = abs(swing_b - swing_a)
    if direction == "up":
        return {
            "1.0": swing_b + 1.0 * diff,
            "1.272": swing_b + 1.272 * diff,
            "1.618": swing_b + 1.618 * diff,
            "2.0": swing_b + 2.0 * diff,
            "2.618": swing_b + 2.618 * diff,
        }
    else:
        return {
            "1.0": swing_b - 1.0 * diff,
            "1.272": swing_b - 1.272 * diff,
            "1.618": swing_b - 1.618 * diff,
            "2.0": swing_b - 2.0 * diff,
            "2.618": swing_b - 2.618 * diff,
        }


def identify_abcd_swing(df: pd.DataFrame, lookback: int = 50) -> ABCDResult | None:
    """Identify the most recent A-B-C-D swing structure.

    A = swing start, B = swing peak/trough, C = retracement bounce.
    Tries to match C to the nearest Fib retracement level.
    """
    if len(df) < lookback:
        return None

    recent = df.iloc[-lookback:]

    # Find swing points
    swing_h_mask = detect_swing_highs(recent, window=2)
    swing_l_mask = detect_swing_lows(recent, window=2)

    swing_highs = list(recent.loc[swing_h_mask, "high"].items())
    swing_lows = list(recent.loc[swing_l_mask, "low"].items())

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return None

    # Determine the dominant swing direction
    last_high_idx, last_high = swing_highs[-1]
    last_low_idx, last_low = swing_lows[-1]

    # Check if last swing was up (low → high → retracement)
    if last_high_idx > last_low_idx:
        # Uptrend: A=low, B=high, C=current pullback
        swing_a = last_low
        swing_b = last_high
        direction = "up"
    else:
        # Downtrend: A=high, B=low, C=current bounce
        swing_a = last_high
        swing_b = last_low
        direction = "down"

    # Calculate where C (current price) is relative to the A-B range
    current_price = df["close"].iloc[-1]
    diff = abs(swing_b - swing_a)
    if diff < 1e-10:
        return None

    if direction == "up":
        retracement_pct = (swing_b - current_price) / diff
    else:
        retracement_pct = (current_price - swing_b) / diff

    # Match to nearest standard Fib level
    best_level = 0.618  # default
    best_dist = abs(retracement_pct - 0.618)
    for level in [0.382, 0.500, 0.618, 0.786]:
        dist = abs(retracement_pct - level)
        if dist < best_dist:
            best_level = level
            best_dist = dist

    # Only accept if within 10% of a Fib level
    if best_dist > 0.10:
        return None

    # Calculate extension target
    extension_ratio = RETRACEMENT_TO_EXTENSION[best_level]
    extensions = fib_extension_levels(swing_a, swing_b, direction)
    target_key = f"{extension_ratio:.3f}"

    if target_key == "1.270":
        target_key = "1.272"

    target_price = extensions.get(target_key)
    if target_price is None:
        return None

    return ABCDResult(
        swing_a=swing_a,
        swing_b=swing_b,
        swing_c=current_price,
        retracement=best_level,
        extension_target=target_price,
        extension_ratio=extension_ratio,
    )


def fib_tp_target(
    entry: float,
    direction: str,
    df: pd.DataFrame,
    sr_levels: list[SRLevel],
    pip_size: float = 0.01,
    clip_pips: float = 10.0,
    lookback: int = 50,
) -> float | None:
    """Determine TP using Fibonacci extension levels.

    Returns the Fib extension target, clipped 10 pips before the nearest S/R.
    Returns None if Fib structure is ambiguous (caller should fall back to ATR TP).
    """
    abcd = identify_abcd_swing(df, lookback)
    if abcd is None:
        return None

    target = abcd.extension_target

    # Verify target is in the right direction
    if direction == "BUY" and target <= entry:
        return None
    if direction == "SELL" and target >= entry:
        return None

    # Clip 10 pips before nearest S/R in the TP direction
    clip_distance = clip_pips * pip_size

    if direction == "BUY":
        # Find nearest resistance above entry but below target
        blockers = [l for l in sr_levels if entry < l.price < target and l.kind == "resistance"]
        if blockers:
            nearest = min(blockers, key=lambda l: l.price)
            clipped = nearest.price - clip_distance
            target = min(target, clipped)
    else:
        # Find nearest support below entry but above target
        blockers = [l for l in sr_levels if target < l.price < entry and l.kind == "support"]
        if blockers:
            nearest = max(blockers, key=lambda l: l.price)
            clipped = nearest.price + clip_distance
            target = max(target, clipped)

    return round(target, 5)
