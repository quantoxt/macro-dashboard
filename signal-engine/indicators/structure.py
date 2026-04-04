"""
Structure Detection — Swing Highs/Lows & S/R Levels
=====================================================
Implements the book-gold rules for dynamic S/R detection.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SRLevel:
    """A single support or resistance level."""
    price: float
    kind: str  # "support" | "resistance"
    strength: int  # how many touches


def detect_swing_highs(df: pd.DataFrame, window: int = 2) -> pd.Series:
    """Boolean series — True where a swing high is detected.

    A swing high: candle's high is greater than `window` candles on each side.
    """
    highs = df["high"]
    result = pd.Series(False, index=df.index)

    for i in range(window, len(df) - window):
        is_swing = True
        for j in range(1, window + 1):
            if highs.iloc[i] <= highs.iloc[i - j] or highs.iloc[i] <= highs.iloc[i + j]:
                is_swing = False
                break
        result.iloc[i] = is_swing

    return result


def detect_swing_lows(df: pd.DataFrame, window: int = 2) -> pd.Series:
    """Boolean series — True where a swing low is detected."""
    lows = df["low"]
    result = pd.Series(False, index=df.index)

    for i in range(window, len(df) - window):
        is_swing = True
        for j in range(1, window + 1):
            if lows.iloc[i] >= lows.iloc[i - j] or lows.iloc[i] >= lows.iloc[i + j]:
                is_swing = False
                break
        result.iloc[i] = is_swing

    return result


def _cluster_levels(prices: list[float], tolerance_pct: float = 0.001) -> list[float]:
    """Cluster nearby price levels and return the mean of each cluster."""
    if not prices:
        return []

    prices = sorted(prices)
    clusters: list[list[float]] = [[prices[0]]]

    for price in prices[1:]:
        if abs(price - clusters[-1][-1]) / clusters[-1][-1] < tolerance_pct:
            clusters[-1].append(price)
        else:
            clusters.append([price])

    return [float(np.mean(c)) for c in clusters]


def detect_support_resistance(
    df: pd.DataFrame,
    window: int = 5,
    tolerance_pct: float = 0.001,
) -> list[SRLevel]:
    """Detect key S/R levels from swing points.

    Returns a list of SRLevel sorted by strength (strongest first).
    Resistance = levels above current price.
    Support = levels below current price.
    """
    current_price = df["close"].iloc[-1]

    swing_h = detect_swing_highs(df, window)
    swing_l = detect_swing_lows(df, window)

    resistance_prices = df.loc[swing_h, "high"].tolist()
    support_prices = df.loc[swing_l, "low"].tolist()

    levels: list[SRLevel] = []

    for price in _cluster_levels(resistance_prices, tolerance_pct):
        if price > current_price:
            levels.append(SRLevel(price=price, kind="resistance", strength=1))

    for price in _cluster_levels(support_prices, tolerance_pct):
        if price < current_price:
            levels.append(SRLevel(price=price, kind="support", strength=1))

    levels.sort(key=lambda l: abs(l.price - current_price))
    return levels


def find_nearest_sr(
    price: float,
    levels: list[SRLevel],
    direction: str,
) -> SRLevel | None:
    """Find the nearest S/R level beyond `price` in the given direction.

    direction="below": find nearest support below price (for BUY SL).
    direction="above": find nearest resistance above price (for SELL SL).
    """
    if direction == "below":
        candidates = [l for l in levels if l.price < price]
        if not candidates:
            return None
        return max(candidates, key=lambda l: l.price)
    else:
        candidates = [l for l in levels if l.price > price]
        if not candidates:
            return None
        return min(candidates, key=lambda l: l.price)
