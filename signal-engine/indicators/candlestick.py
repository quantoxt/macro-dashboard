"""
Candlestick Pattern Detection
==============================
Book-rule implementations with:
- 60% close validation (morning/evening star)
- Wick proximity (tweezers — not adjacency)
- Trend-direction filter
- Signal strength 0.0-1.0
"""

import pandas as pd
import numpy as np


def _body(row: pd.Series) -> float:
    return abs(row["close"] - row["open"])


def _upper_wick(row: pd.Series) -> float:
    return row["high"] - max(row["close"], row["open"])


def _lower_wick(row: pd.Series) -> float:
    return min(row["close"], row["open"]) - row["low"]


def _is_bullish(row: pd.Series) -> bool:
    return row["close"] > row["open"]


def _is_bearish(row: pd.Series) -> bool:
    return row["close"] < row["open"]


def _body_range(row: pd.Series) -> float:
    return max(row["high"] - row["low"], 1e-10)


def _trend_direction(df: pd.DataFrame, lookback: int = 10) -> str:
    """Simple trend: compare current close to SMA of `lookback` periods."""
    if len(df) < lookback:
        return "neutral"
    sma_val = df["close"].iloc[-lookback:].mean()
    current = df["close"].iloc[-1]
    if current > sma_val * 1.001:
        return "up"
    elif current < sma_val * 0.999:
        return "down"
    return "neutral"


def detect_morning_star(df: pd.DataFrame, min_strength: float = 0.3) -> float:
    """Morning star detection with 60% close validation.

    Pattern: large bearish candle -> 1-4 indecision candles -> bullish candle
    closing beyond 60% of the first bearish candle body (from the bottom).

    Returns signal strength 0.0-1.0 (0 = no signal).
    """
    if len(df) < 7:
        return 0.0

    trend = _trend_direction(df)
    if trend == "down" or trend == "neutral":
        pass  # morning star is valid in downtrend or neutral
    else:
        return 0.0  # skip in uptrend per book rules

    strength = 0.0
    last = df.iloc[-1]
    first = df.iloc[-3]  # the initial bearish candle (3 candles back)

    # First candle must be bearish
    if not _is_bearish(first):
        return 0.0

    # Last candle must be bullish
    if not _is_bullish(last):
        return 0.0

    # Middle candle(s) should be small (indecision)
    middle = df.iloc[-2]
    if _body(middle) > _body(first) * 0.5:
        return 0.0

    # 60% close rule: last candle closes above 60% of first candle's body
    first_body_bottom = min(first["open"], first["close"])
    first_body_top = max(first["open"], first["close"])
    first_body_range = first_body_top - first_body_bottom
    if first_body_range < 1e-10:
        return 0.0

    recovery = (last["close"] - first_body_bottom) / first_body_range
    if recovery >= 0.6:
        strength = min(1.0, recovery)

    return strength if strength >= min_strength else 0.0


def detect_evening_star(df: pd.DataFrame, min_strength: float = 0.3) -> float:
    """Evening star detection with 60% close validation.

    Pattern: large bullish candle -> 1-4 indecision candles -> bearish candle
    closing beyond 60% of the first bullish candle body (from the top).

    Returns signal strength 0.0-1.0.
    """
    if len(df) < 7:
        return 0.0

    trend = _trend_direction(df)
    if trend != "up" and trend != "neutral":
        return 0.0  # skip in downtrend

    last = df.iloc[-1]
    first = df.iloc[-3]

    if not _is_bullish(first):
        return 0.0
    if not _is_bearish(last):
        return 0.0

    middle = df.iloc[-2]
    if _body(middle) > _body(first) * 0.5:
        return 0.0

    first_body_bottom = min(first["open"], first["close"])
    first_body_top = max(first["open"], first["close"])
    first_body_range = first_body_top - first_body_bottom
    if first_body_range < 1e-10:
        return 0.0

    decline = (first_body_top - last["close"]) / first_body_range
    strength = min(1.0, decline)

    return strength if strength >= min_strength else 0.0


def detect_tweezer_bottoms(df: pd.DataFrame, tolerance_pips: float = 5.0, pip_size: float = 0.01) -> float:
    """Tweezer bottoms — two+ candles with long lower wicks at similar lows.

    Candles don't need to be adjacent (book rule: proximity, not adjacency).
    Returns strength 0.0-1.0.
    """
    if len(df) < 10:
        return 0.0

    trend = _trend_direction(df)
    if trend == "up":
        return 0.0

    tolerance = tolerance_pips * pip_size
    recent = df.iloc[-10:]

    # Find candles with significant lower wicks (at least 60% of total range)
    wicky = []
    for idx, row in recent.iterrows():
        total_range = _body_range(row)
        if total_range < 1e-10:
            continue
        lw_ratio = _lower_wick(row) / total_range
        if lw_ratio >= 0.6:
            wicky.append(row["low"])

    if len(wicky) < 2:
        return 0.0

    # Check for proximity between any two wicky candle lows
    wicky.sort()
    for i in range(len(wicky) - 1):
        if abs(wicky[i + 1] - wicky[i]) <= tolerance:
            return 0.8

    return 0.0


def detect_tweezer_tops(df: pd.DataFrame, tolerance_pips: float = 5.0, pip_size: float = 0.01) -> float:
    """Tweezer tops — two+ candles with long upper wicks at similar highs.

    Returns strength 0.0-1.0.
    """
    if len(df) < 10:
        return 0.0

    trend = _trend_direction(df)
    if trend == "down":
        return 0.0

    tolerance = tolerance_pips * pip_size
    recent = df.iloc[-10:]

    wicky = []
    for idx, row in recent.iterrows():
        total_range = _body_range(row)
        if total_range < 1e-10:
            continue
        uw_ratio = _upper_wick(row) / total_range
        if uw_ratio >= 0.6:
            wicky.append(row["high"])

    if len(wicky) < 2:
        return 0.0

    wicky.sort()
    for i in range(len(wicky) - 1):
        if abs(wicky[i + 1] - wicky[i]) <= tolerance:
            return 0.8

    return 0.0


def detect_engulfing(df: pd.DataFrame) -> float:
    """Bullish/bearish engulfing detection.

    Returns strength 0.0-1.0. Positive = bullish engulfing, sign embedded in magnitude.
    """
    if len(df) < 3:
        return 0.0

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # Bullish engulfing
    if _is_bearish(prev) and _is_bullish(curr):
        if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
            engulf_strength = _body(curr) / max(_body(prev), 1e-10)
            return min(1.0, engulf_strength / 2.0)

    # Bearish engulfing
    if _is_bullish(prev) and _is_bearish(curr):
        if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
            engulf_strength = _body(curr) / max(_body(prev), 1e-10)
            return min(1.0, engulf_strength / 2.0)

    return 0.0


def detect_rejection_wick(df: pd.DataFrame, min_ratio: float = 0.65) -> float:
    """Detect candle with long rejection wick (pin bar).

    Returns strength 0.0-1.0.
    """
    if len(df) < 2:
        return 0.0

    row = df.iloc[-1]
    total_range = _body_range(row)
    if total_range < 1e-10:
        return 0.0

    lower_ratio = _lower_wick(row) / total_range
    upper_ratio = _upper_wick(row) / total_range

    if lower_ratio >= min_ratio and _is_bullish(row):
        return lower_ratio
    if upper_ratio >= min_ratio and _is_bearish(row):
        return upper_ratio

    return 0.0
