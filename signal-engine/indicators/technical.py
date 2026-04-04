"""
Technical Indicators
====================
Pandas-based technical indicator calculations.
Ported from resources/blue-star-indicators.py — cleaned up, type-hinted, no MT5.
"""

import numpy as np
import pandas as pd


def ema(data: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return data.ewm(span=period, adjust=False).mean()


def sma(data: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return data.rolling(window=period).mean()


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (0-100)."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    data: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD. Returns (macd_line, signal_line, histogram)."""
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    data: pd.Series, period: int = 20, std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands. Returns (upper, middle, lower)."""
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range. DataFrame must have 'high', 'low', 'close'."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.rolling(window=period).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index (0-100)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where(plus_dm > 0, 0.0)
    minus_dm = minus_dm.where(minus_dm > 0, 0.0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_val = tr.rolling(window=period).mean()
    plus_di = 100.0 * (plus_dm.rolling(window=period).mean() / atr_val)
    minus_di = 100.0 * (minus_dm.rolling(window=period).mean() / atr_val)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(window=period).mean()


def stochastic(
    df: pd.DataFrame, k_period: int = 14, d_period: int = 3
) -> tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator. Returns (%K, %D)."""
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()

    k = 100.0 * (df["close"] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return k, d


def average_atr(df: pd.DataFrame, period: int = 14, avg_period: int = 20) -> pd.Series:
    """Rolling average of ATR — used to check if ATR is expanding or contracting."""
    atr_series = atr(df, period)
    return atr_series.rolling(window=avg_period).mean()


def consecutive_extreme(
    series: pd.Series,
    threshold: float,
    direction: str,
    bars: int = 2,
) -> bool:
    """Check if series has been below/above threshold for N consecutive bars.

    Args:
        series: indicator series (e.g., RSI, MACD histogram)
        threshold: the threshold value
        direction: "below" or "above"
        bars: number of consecutive bars required

    Returns:
        True if the condition holds for all N most-recent bars.
    """
    if len(series) < bars + 1:
        return False

    for i in range(1, bars + 1):
        val = series.iloc[-i]
        if pd.isna(val):
            return False
        if direction == "below" and val >= threshold:
            return False
        if direction == "above" and val <= threshold:
            return False

    return True
