"""
Yahoo Finance Data Fetcher
===========================
Fetches OHLC data from Yahoo Finance using yfinance.
Aggregates 1h candles into 4h. Handles null candles and rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from config import EngineConfig, get_config
from data.cache import DataCache

logger = logging.getLogger(__name__)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where open or close is null, ensure correct dtypes."""
    df = df.dropna(subset=["open", "close"])
    df = df.astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )
    return df


def aggregate_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 1h candles into 4h candles.

    Groups every 4 consecutive rows (chronological order assumed).
    """
    if len(df_1h) < 4:
        return pd.DataFrame()

    records = []
    values = df_1h.to_dict("records")

    for i in range(0, len(values) - 3, 4):
        chunk = values[i : i + 4]
        records.append(
            {
                "datetime": chunk[0]["datetime"],
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c["volume"] for c in chunk),
            }
        )

    return pd.DataFrame(records)


def fetch_ohlc(
    ticker: str,
    interval: str = "1h",
    lookback_days: int = 100,
) -> pd.DataFrame:
    """Fetch OHLC data from Yahoo Finance.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. 'GC=F').
        interval: Yahoo interval string ('1h', '1d', etc.).
        lookback_days: How far back to fetch.

    Returns:
        DataFrame with columns: datetime, open, high, low, close, volume.
        Empty DataFrame on failure.
    """
    try:
        period1 = (datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)).strftime(
            "%Y-%m-%d"
        )

        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(start=period1, interval=interval, auto_adjust=True)

        if hist.empty:
            logger.warning("No data returned for %s @ %s", ticker, interval)
            return pd.DataFrame(
                columns=["datetime", "open", "high", "low", "close", "volume"]
            )

        hist = hist.reset_index()
        # yfinance returns a DatetimeIndex column — normalize the name
        date_col = [c for c in hist.columns if "date" in c.lower() or c == "index"][0]
        hist = hist.rename(columns={date_col: "datetime"})
        hist = hist.rename(columns=str.lower)
        hist = hist[["datetime", "open", "high", "low", "close", "volume"]]

        hist = _clean_dataframe(hist)
        hist = hist.reset_index(drop=True)

        logger.info(
            "Fetched %d candles for %s @ %s", len(hist), ticker, interval
        )
        return hist

    except Exception as exc:
        logger.error("Failed to fetch %s @ %s: %s", ticker, interval, exc)
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])


async def fetch_multi_timeframe(
    instrument_symbol: str,
    config: EngineConfig | None = None,
    cache: DataCache | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch both H1 and H4 candles for an instrument.

    H4 is derived by aggregating 1h candles (same approach as v1).

    Returns:
        {"H1": pd.DataFrame, "H4": pd.DataFrame}
    """
    if config is None:
        config = get_config()
    if cache is None:
        cache = DataCache()

    inst = config.get_instrument(instrument_symbol)
    ticker = inst.yahoo_ticker

    result: dict[str, pd.DataFrame] = {}

    # --- H1 ---
    h1_cached = cache.get(ticker, "1h")
    if h1_cached is not None:
        result["H1"] = h1_cached
    else:
        h1_df = await asyncio.to_thread(
            fetch_ohlc, ticker, "1h", config.h1_lookback_days
        )
        cache.set(ticker, "1h", h1_df, ttl=config.cache_ttl_h1)
        result["H1"] = h1_df

    # --- H4 (aggregate from 1h with longer lookback) ---
    h4_cached = cache.get(ticker, "4h")
    if h4_cached is not None:
        result["H4"] = h4_cached
    else:
        h4_raw = await asyncio.to_thread(
            fetch_ohlc, ticker, "1h", config.h4_lookback_days
        )
        h4_df = aggregate_to_4h(h4_raw)
        cache.set(ticker, "4h", h4_df, ttl=config.cache_ttl_h4)
        result["H4"] = h4_df

        # small delay to be respectful to Yahoo
        await asyncio.sleep(config.request_delay_ms / 1000.0)

    return result
