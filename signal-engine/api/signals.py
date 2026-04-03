"""
Signals API
============
GET /signals          — all active signals across instruments
GET /signals/{instrument} — signals for a specific instrument

Runs all 3 strategies per instrument, returns combined signals.
Includes news calendar auto-pause.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from config import get_config
from data.cache import DataCache
from data.fetcher import fetch_multi_timeframe
from indicators.news import check_news_pause, fetch_economic_calendar
from strategies.base import Signal
from strategies.confluence_breakout import ConfluenceBreakout
from strategies.mean_reversion import MeanReversion
from strategies.momentum_shift import MomentumShift
from api.config import is_strategy_enabled
from tracker.tracker import SignalTracker
from tracker.storage import SignalStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals")

# Module-level instances — shared across requests
_cache = DataCache()
_strategies = [
    ConfluenceBreakout(),
    MeanReversion(),
    MomentumShift(),
]

# Tracker — initialized in main.py, set here for access
_tracker: SignalTracker | None = None


def set_tracker(tracker: SignalTracker) -> None:
    global _tracker
    _tracker = tracker


def _signal_to_dict(sig: Signal) -> dict:
    """Convert a Signal dataclass to the API response shape."""
    return {
        "instrument": sig.instrument,
        "direction": sig.direction,
        "confidence": sig.confidence,
        "entry": sig.entry,
        "stopLoss": sig.stop_loss,
        "takeProfit": sig.take_profit,
        "riskReward": sig.risk_reward,
        "strategy": sig.strategy,
        "timeframe": sig.timeframe,
        "reasons": sig.reasons,
        "generatedAt": sig.generated_at,
    }


@router.get("")
async def get_all_signals() -> dict:
    """Fetch and evaluate signals for all instruments."""
    config = get_config()

    # Check news pause
    events = await fetch_economic_calendar()
    news = check_news_pause(events, pause_minutes=config.news_pause_minutes)

    if news.pause_active:
        logger.info("News pause active: %s", news.reason)

    signals: list[dict] = []

    for inst in config.instruments:
        try:
            inst_signals = await _evaluate_instrument(inst.symbol, news)
            for sig in inst_signals:
                signals.append(_signal_to_dict(sig))
        except Exception as exc:
            logger.error("Error evaluating %s: %s", inst.symbol, exc)

    return {
        "signals": signals,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{instrument}")
async def get_instrument_signals(instrument: str) -> dict:
    """Fetch and evaluate signals for a single instrument."""
    config = get_config()

    try:
        config.get_instrument(instrument)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown instrument: {instrument}")

    events = await fetch_economic_calendar()
    news = check_news_pause(events, pause_minutes=config.news_pause_minutes)

    try:
        sigs = await _evaluate_instrument(instrument, news)
        signals = [_signal_to_dict(s) for s in sigs]
    except Exception as exc:
        logger.error("Error evaluating %s: %s", instrument, exc)
        signals = []

    return {
        "signals": signals,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


async def _evaluate_instrument(
    instrument: str, news: "NewsPauseResult | None" = None
) -> list[Signal]:
    """Fetch data and run all strategies for one instrument."""
    config = get_config()
    results: list[Signal] = []

    data = await fetch_multi_timeframe(instrument, config, _cache)

    h1_df = data.get("H1")
    h4_df = data.get("H4")

    if h1_df is None or h4_df is None or h1_df.empty or h4_df.empty:
        logger.warning("No data for %s", instrument)
        return results

    inst = config.get_instrument(instrument)

    for strategy in _strategies:
        try:
            # Check if strategy is enabled via config API
            if not is_strategy_enabled(strategy.name):
                continue

            # News pause only blocks confluence_breakout and momentum_shift
            # Mean reversion is allowed during news (it's counter-trend)
            if news and news.pause_active and strategy.name != "mean_reversion":
                logger.debug(
                    "%s: skipped for %s due to news pause", strategy.name, instrument
                )
                continue

            sig = strategy.evaluate(instrument, h1_df, h4_df, pip_size=inst.pip_size)
            if sig is not None:
                # Auto-track the signal
                if _tracker is not None:
                    _tracker.track_signal(sig)
                results.append(sig)
        except Exception as exc:
            logger.error(
                "Strategy %s failed for %s: %s", strategy.name, instrument, exc
            )

    return results
