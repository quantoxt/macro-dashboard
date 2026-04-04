"""
Z-Score Indicator
==================
Measures how many standard deviations price is from its N-period mean.
Useful for mean reversion: extreme Z-Scores indicate overbought/oversold conditions.
"""

import pandas as pd


def zscore(series: pd.Series, period: int = 20) -> pd.Series:
    """Calculate Z-Score: (price - mean) / std over N periods.

    Returns a Series with same index as input. Values near 0 = normal,
    values > 2 = overbought, values < -2 = oversold.

    First `period` values will be NaN.
    """
    mean = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return (series - mean) / std


def zscore_at_last(series: pd.Series, period: int = 20) -> float | None:
    """Get the Z-Score value at the most recent bar.

    Returns None if not enough data for calculation.
    """
    zs = zscore(series, period)
    val = zs.iloc[-1]
    return val if pd.notna(val) else None


def check_zscore_extremes(
    series: pd.Series, period: int = 20, entry_threshold: float = 2.0
) -> dict:
    """Check if Z-Score is at extreme levels for mean reversion entry.

    Returns dict with:
    - value: current Z-Score
    - is_oversold: Z-Score < -threshold (BUY candidate)
    - is_overbought: Z-Score > +threshold (SELL candidate)
    - severity: how extreme (mild/moderate/extreme based on distance from threshold)
    """
    val = zscore_at_last(series, period)
    if val is None:
        return {"value": None, "is_oversold": False, "is_overbought": False, "severity": "none"}

    abs_val = abs(val)
    severity = "mild" if abs_val < entry_threshold + 0.5 else (
        "moderate" if abs_val < entry_threshold + 1.0 else "extreme"
    )

    return {
        "value": round(val, 3),
        "is_oversold": val < -entry_threshold,
        "is_overbought": val > entry_threshold,
        "severity": severity,
    }
