"""
Market Pulse API
================
GET /market-pulse — aggregated market overview (session, regime, volatility, news, consolidation)
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from config import get_config
from data.cache import DataCache
from data.fetcher import fetch_ohlc
from indicators.news import (
    CalendarEvent,
    fetch_economic_calendar,
    get_current_session,
    _is_high_impact,
    _parse_event_datetime,
)
from indicators.technical import adx, atr, ema
from strategies.consolidation_detector import detect_consolidation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-pulse")

# Simple TTL cache for the response
_cache: dict[str, Any] | None = None
_cache_ts: float = 0.0
_CACHE_TTL: float = 150.0  # 2.5 minutes


def _get_session_info() -> tuple[str, str]:
    """Return (session_name, session_time) based on current UTC hour."""
    hour = datetime.now(timezone.utc).hour
    weekday = datetime.now(timezone.utc).weekday()  # 0=Mon, 6=Sun

    # Weekend
    if weekday >= 5:
        return "Closed", "—"

    # Overlap: 12–16 UTC (London + New York)
    if 12 <= hour < 16:
        return "London / New York", "12:00–16:00 UTC"

    # New York: 12–21 UTC
    if 12 <= hour < 21:
        return "New York", "12:00–21:00 UTC"

    # London: 7–16 UTC
    if 7 <= hour < 16:
        return "London", "07:00–16:00 UTC"

    # Asian: 0–7 UTC
    if 0 <= hour < 7:
        return "Asian", "00:00–07:00 UTC"

    # After hours: 21–00 UTC
    return "Closed", "21:00–00:00 UTC"


async def _compute_regime_and_volatility() -> tuple[str, int, float, str]:
    """Fetch data for all instruments, compute regime + volatility.

    Returns (regime, confidence, volatilityIndex, volatilityLabel).
    """
    config = get_config()
    cache = DataCache()

    bullish = 0
    bearish = 0
    ranging = 0
    total = 0
    atr_pcts: list[float] = []

    for inst in config.instruments:
        try:
            df = await asyncio.to_thread(
                fetch_ohlc, inst.yahoo_ticker, "1h", 30
            )
            if df.empty or len(df) < 25:
                continue

            total += 1

            # --- Regime: ADX + EMA slope ---
            adx_series = adx(df, 14)
            ema20 = ema(df["close"], 20)

            latest_adx = adx_series.iloc[-1] if not adx_series.empty else 0.0
            # EMA slope: compare last value to 5 bars ago
            if len(ema20) >= 6:
                slope = ema20.iloc[-1] - ema20.iloc[-6]
            else:
                slope = 0.0

            if latest_adx > 20:
                if slope > 0:
                    bullish += 1
                else:
                    bearish += 1
            else:
                ranging += 1

            # --- Volatility: ATR normalized as % of price ---
            atr_series = atr(df, 14)
            if not atr_series.empty:
                latest_atr = atr_series.iloc[-1]
                latest_close = df["close"].iloc[-1]
                if latest_close > 0:
                    atr_pcts.append((latest_atr / latest_close) * 100.0)

        except Exception as exc:
            logger.error("Regime/vol calc failed for %s: %s", inst.symbol, exc)

    # Regime decision
    if total == 0:
        return "neutral", 0, 0.0, "Low"

    if bullish >= 3:
        regime = "risk-on"
        confidence = int((bullish / total) * 100)
    elif bearish >= 3:
        regime = "risk-off"
        confidence = int((bearish / total) * 100)
    else:
        regime = "neutral"
        agreement = max(bullish, bearish, ranging)
        confidence = int((agreement / total) * 100)

    # Volatility
    if atr_pcts:
        vol_index = round(sum(atr_pcts) / len(atr_pcts), 2)
    else:
        vol_index = 0.0

    if vol_index < 0.5:
        vol_label = "Low"
    elif vol_index <= 1.5:
        vol_label = "Moderate"
    else:
        vol_label = "High"

    return regime, confidence, vol_index, vol_label


async def _compute_consolidation() -> list[str]:
    """Check each instrument for consolidation. Returns list of consolidating symbols."""
    config = get_config()
    consolidating: list[str] = []

    for inst in config.instruments:
        try:
            df = await asyncio.to_thread(
                fetch_ohlc, inst.yahoo_ticker, "1h", 30
            )
            if df.empty or len(df) < 20:
                continue

            result = detect_consolidation(df, pip_size=inst.pip_size)
            if result.is_consolidating:
                consolidating.append(inst.symbol)

        except Exception as exc:
            logger.error("Consolidation check failed for %s: %s", inst.symbol, exc)

    return consolidating


def _compute_news(events: list[CalendarEvent]) -> tuple[int, str, str]:
    """Count upcoming high-impact events and find the next one.

    Returns (newsWarnings, nextEvent, nextEventTime).
    """
    now = datetime.now(timezone.utc)
    warnings = 0
    next_event_title = "No major events"
    next_event_time = "—"
    closest_diff: float | None = None

    for event in events:
        if not _is_high_impact(event):
            continue

        event_time = _parse_event_datetime(event.date_str)
        if event_time is None:
            continue

        diff_minutes = (event_time - now).total_seconds() / 60.0

        # Count events in the next 2 hours
        if 0 < diff_minutes <= 120:
            warnings += 1

        # Track the nearest upcoming event
        if diff_minutes > 0:
            if closest_diff is None or diff_minutes < closest_diff:
                closest_diff = diff_minutes
                next_event_title = event.title
                next_event_time = event_time.strftime("%H:%M") + " UTC"

    return warnings, next_event_title, next_event_time


@router.get("")
async def get_market_pulse() -> dict[str, Any]:
    """Aggregated market overview."""
    global _cache, _cache_ts

    # Return cached response if fresh
    now = time.monotonic()
    if _cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    # Compute all fields — graceful degradation per section
    try:
        session, session_time = _get_session_info()
    except Exception:
        session, session_time = "Closed", "—"

    try:
        regime, confidence, vol_index, vol_label = await _compute_regime_and_volatility()
    except Exception as exc:
        logger.error("Failed to compute regime/volatility: %s", exc)
        regime, confidence, vol_index, vol_label = "neutral", 0, 0.0, "Low"

    try:
        events = await fetch_economic_calendar()
        news_warnings, next_event, next_event_time = _compute_news(events)
    except Exception as exc:
        logger.error("Failed to compute news: %s", exc)
        news_warnings, next_event, next_event_time = 0, "No major events", "—"

    try:
        consolidation_pairs = await _compute_consolidation()
    except Exception as exc:
        logger.error("Failed to compute consolidation: %s", exc)
        consolidation_pairs = []

    result = {
        "session": session,
        "sessionTime": session_time,
        "regime": regime,
        "regimeConfidence": confidence,
        "volatilityIndex": vol_index,
        "volatilityLabel": vol_label,
        "newsWarnings": news_warnings,
        "consolidationPairs": consolidation_pairs,
        "nextEvent": next_event,
        "nextEventTime": next_event_time,
    }

    _cache = result
    _cache_ts = time.monotonic()

    return result
