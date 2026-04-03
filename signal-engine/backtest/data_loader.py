"""
Historical Data Loader for Backtesting
========================================
Fetches OHLC data from Yahoo Finance for date ranges, with CSV caching.
Pluggable — swap Yahoo for any data source later.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(symbol: str, interval: str) -> Path:
    safe = symbol.replace("=", "_").replace("^", "_")
    return CACHE_DIR / f"{safe}_{interval}.csv"


def _load_cache(symbol: str, interval: str) -> pd.DataFrame | None:
    path = _cache_path(symbol, interval)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["datetime"])
        logger.debug("Cache hit: %s %s (%d rows)", symbol, interval, len(df))
        return df
    except Exception:
        return None


def _save_cache(symbol: str, interval: str, df: pd.DataFrame) -> None:
    path = _cache_path(symbol, interval)
    df.to_csv(path, index=False)
    logger.debug("Cached: %s %s (%d rows)", symbol, interval, len(df))


def fetch_historical(
    yahoo_ticker: str,
    interval: str = "1h",
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch historical OHLC data for a date range.

    Args:
        yahoo_ticker: Yahoo Finance ticker (e.g. 'GC=F', 'BTC-USD').
        interval: Yahoo interval ('1h', '1d').
        start_date: Start of date range.
        end_date: End of date range.
        use_cache: Read/write CSV cache.

    Returns:
        DataFrame with columns: datetime, open, high, low, close, volume.
    """
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)

    # Try cache first
    if use_cache:
        cached = _load_cache(yahoo_ticker, interval)
        if cached is not None and not cached.empty:
            # Filter to date range if specified
            if start_date is not None:
                start_ts = pd.Timestamp(start_date)
                cached = cached[cached["datetime"] >= start_ts]
            if end_date is not None:
                end_ts = pd.Timestamp(end_date)
                cached = cached[cached["datetime"] <= end_ts]
            if not cached.empty:
                return cached.reset_index(drop=True)

    # Fetch from Yahoo
    try:
        period1 = start_date or (datetime.now(tz=timezone.utc) - timedelta(days=730))
        period1_str = period1.strftime("%Y-%m-%d") if isinstance(period1, datetime) else str(period1)

        ticker_obj = yf.Ticker(yahoo_ticker)
        hist = ticker_obj.history(start=period1_str, interval=interval, auto_adjust=True)

        if hist.empty:
            logger.warning("No data for %s @ %s", yahoo_ticker, interval)
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

        hist = hist.reset_index()
        date_col = [c for c in hist.columns if "date" in c.lower() or c in ("index", "Date")][0]
        hist = hist.rename(columns={date_col: "datetime"})
        hist = hist.rename(columns=str.lower)
        hist = hist[["datetime", "open", "high", "low", "close", "volume"]]
        hist = hist.dropna(subset=["open", "close"])
        hist = hist.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        hist = hist.reset_index(drop=True)

        # Save full dataset to cache (not filtered)
        if use_cache:
            _save_cache(yahoo_ticker, interval, hist)

        # Filter to date range
        if start_date is not None:
            start_ts = pd.Timestamp(start_date)
            hist = hist[hist["datetime"] >= start_ts]
        if end_date is not None:
            end_ts = pd.Timestamp(end_date)
            hist = hist[hist["datetime"] <= end_ts]

        logger.info("Fetched %d candles for %s @ %s", len(hist), yahoo_ticker, interval)
        return hist.reset_index(drop=True)

    except Exception as exc:
        logger.error("Failed to fetch %s @ %s: %s", yahoo_ticker, interval, exc)
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
