"""
Signals API
============
GET /signals          — all active signals across instruments
GET /signals/{instrument} — signals for a specific instrument
GET /signals/refresh  — force a signal refresh

Runs all 3 strategies per instrument, returns combined signals.
Includes news calendar auto-pause, dedup, cooldown, and auto-refresh.
"""

import asyncio
import logging
import time
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

# Tracker + Storage — initialized in main.py, set here for access
_tracker: SignalTracker | None = None
_storage: SignalStorage | None = None

# Cooldown tracking: (instrument, strategy) -> resolved_at timestamp
_resolved_timestamps: dict[tuple[str, str], float] = {}

# Auto-refresh state
_cached_signals: list[dict] = []
_last_refresh_time: float = 0.0
_auto_refresh_lock: asyncio.Lock = asyncio.Lock()


def set_tracker(tracker: SignalTracker) -> None:
    global _tracker
    _tracker = tracker


def set_storage(storage: SignalStorage) -> None:
    global _storage
    _storage = storage


def _is_on_cooldown(instrument: str, strategy: str) -> bool:
    """Check if instrument+strategy is in cooldown after a recent resolved signal."""
    config = get_config()
    cooldown_seconds = config.signal_cooldown_hours * 3600
    key = (instrument, strategy)
    if key in _resolved_timestamps:
        elapsed = time.time() - _resolved_timestamps[key]
        if elapsed < cooldown_seconds:
            return True
        else:
            del _resolved_timestamps[key]  # expired
    return False


def _update_cooldown_from_resolved() -> None:
    """Scan resolved signals and update cooldown timestamps."""
    if _storage is None:
        return
    for s in _storage.get_all():
        if s.outcome in ("WIN", "LOSS", "EXPIRED"):
            key = (s.instrument, s.strategy)
            if key not in _resolved_timestamps:
                try:
                    ts = datetime.fromisoformat(s.generated_at).timestamp()
                    _resolved_timestamps[key] = ts
                except (ValueError, TypeError):
                    pass


def _count_signals_today(instrument: str) -> int:
    """Count signals generated today for a given instrument (from cache + storage)."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    count = sum(
        1 for s in _cached_signals
        if s["instrument"] == instrument and s.get("generatedAt", "") >= today_start
    )
    if _storage is not None:
        count += sum(
            1 for s in _storage.get_all()
            if s.instrument == instrument
            and s.generated_at >= today_start
            and s.outcome is None  # only pending count toward limit
        )
    return count


def _merge_correlated_signals(signals: list[dict]) -> list[dict]:
    """Merge signals from multiple strategies for the same instrument+direction.

    - Same instrument + same direction → merge into one signal
    - Keep highest confidence as base, boost +10 per additional strategy
    - Different directions on same instrument → keep both (contradiction)
    """
    from collections import defaultdict

    config = get_config()
    if not config.correlation_merge_enabled:
        # Still add strategyCount field
        for sig in signals:
            sig.setdefault("strategyCount", 1)
            sig.setdefault("agreeingStrategies", [sig["strategy"]])
        return signals

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for sig in signals:
        key = (sig["instrument"], sig["direction"])
        groups[key].append(sig)

    merged: list[dict] = []

    for (instrument, direction), group in groups.items():
        if len(group) == 1:
            sig = group[0]
            sig["strategyCount"] = 1
            sig["agreeingStrategies"] = [sig["strategy"]]
            merged.append(sig)
        else:
            sorted_group = sorted(group, key=lambda s: s.get("confidence", 0), reverse=True)
            base = sorted_group[0].copy()

            all_strategies = [s["strategy"] for s in sorted_group]
            bonus = (len(sorted_group) - 1) * config.correlation_confidence_bonus
            base["confidence"] = min(100, base.get("confidence", 0) + bonus)

            # Merge reasons (deduplicated)
            all_reasons: list[str] = []
            seen: set[str] = set()
            for s in sorted_group:
                for r in s.get("reasons", []):
                    if r not in seen:
                        all_reasons.append(r)
                        seen.add(r)
            base["reasons"] = all_reasons

            base["strategyCount"] = len(sorted_group)
            base["agreeingStrategies"] = all_strategies
            base["reasons"].append(
                f"Multi-strategy confluence ({len(sorted_group)} agree)"
            )

            merged.append(base)

    return merged


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
    """Return signals. Uses cache if fresh, otherwise evaluates fresh."""
    global _cached_signals, _last_refresh_time
    config = get_config()
    age = time.time() - _last_refresh_time

    # Return cached if fresh
    if _cached_signals and age < config.auto_refresh_interval:
        return {
            "signals": _cached_signals,
            "updatedAt": datetime.fromtimestamp(_last_refresh_time, tz=timezone.utc).isoformat(),
            "source": "cache",
        }

    # Stale or empty — do fresh evaluation
    events = await fetch_economic_calendar()
    news = check_news_pause(events, pause_minutes=config.news_pause_minutes)

    if news.pause_active:
        logger.info("News pause active: %s", news.reason)

    # VIX regime check
    vix_regime = "unknown"
    vix_description = ""
    if config.vix_enabled:
        try:
            from indicators.vix import fetch_vix_with_sma
            vix_data = await fetch_vix_with_sma(config.vix_sma_period)
            vix_regime = vix_data["regime"]
            vix_description = vix_data["description"]
            if vix_regime == "high_fear":
                logger.warning("VIX high-fear regime: %s", vix_description)
        except Exception as exc:
            logger.error("VIX check failed: %s", exc)

    signals: list[dict] = []

    for inst in config.instruments:
        try:
            inst_signals = await _evaluate_instrument(inst.symbol, news)
            for sig in inst_signals:
                sig_dict = _signal_to_dict(sig)
                # Apply VIX penalty if in high-fear regime
                if vix_regime == "high_fear":
                    sig_dict["confidence"] = max(0, sig_dict["confidence"] - 15)
                signals.append(sig_dict)
        except Exception as exc:
            logger.error("Error evaluating %s: %s", inst.symbol, exc)

    # Update cache
    _cached_signals = signals
    _last_refresh_time = time.time()

    result: dict = {
        "signals": signals,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "fresh",
    }
    if config.vix_enabled:
        result["vixRegime"] = vix_regime
        result["vixDescription"] = vix_description

    return result


@router.get("/refresh")
async def manual_refresh() -> dict:
    """Force a signal refresh outside the auto-schedule."""
    count = await auto_refresh_signals()
    return {
        "refreshed": True,
        "newSignals": count,
        "totalActive": len(_cached_signals),
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

    # Update cooldown tracker from resolved signals
    _update_cooldown_from_resolved()

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
                # Dedup: check if a pending signal with same instrument+direction+strategy exists
                if _storage is not None:
                    pending = _storage.get_pending()
                    is_dup = any(
                        p.instrument == sig.instrument
                        and p.direction == sig.direction
                        and p.strategy == sig.strategy
                        for p in pending
                    )
                    if is_dup:
                        logger.info(
                            "Dedup: skipped %s %s for %s — pending signal already tracked",
                            sig.strategy, sig.direction, sig.instrument
                        )
                        continue

                # Cooldown: check if signal was recently resolved for same instrument+strategy
                if _is_on_cooldown(sig.instrument, sig.strategy):
                    logger.info(
                        "Dedup: skipped %s for %s — cooldown active",
                        sig.strategy, sig.instrument
                    )
                    continue

                # Auto-track + collect
                tracked_ref = ""
                if _tracker is not None:
                    tracked = _tracker.track_signal(sig)
                    tracked_ref = tracked.signal_ref

                # Notify via Telegram
                try:
                    from notifier.telegram import get_notifier
                    notifier = get_notifier()
                    if notifier is not None:
                        sig_dict = _signal_to_dict(sig)
                        sig_dict["signal_ref"] = tracked_ref
                        await notifier.send_signal(sig_dict)
                except Exception as exc:
                    logger.debug("Notifier call failed: %s", exc)

                results.append(sig)
        except Exception as exc:
            logger.error(
                "Strategy %s failed for %s: %s", strategy.name, instrument, exc
            )

    return results


async def auto_refresh_signals() -> int:
    """Fetch data + run strategies for all instruments. Return count of new signals.

    Called by the background task in main.py and by the manual refresh endpoint.
    """
    global _cached_signals, _last_refresh_time

    async with _auto_refresh_lock:
        config = get_config()

        # Fetch news (will use cache if fresh)
        events = await fetch_economic_calendar()
        news = check_news_pause(events, pause_minutes=config.news_pause_minutes)

        # VIX regime check
        vix_regime = "unknown"
        if config.vix_enabled:
            try:
                from indicators.vix import fetch_vix_with_sma
                vix_data = await fetch_vix_with_sma(config.vix_sma_period)
                vix_regime = vix_data["regime"]
            except Exception:
                pass

        all_signals: list[dict] = []
        new_count = 0

        for inst in config.instruments:
            try:
                # Frequency limit check
                if config.signal_frequency_limits_enabled:
                    today_count = _count_signals_today(inst.symbol)
                    if today_count >= inst.max_signals_per_day:
                        logger.info(
                            "Signal limit: %s at %d/%d for today — skipping",
                            inst.symbol, today_count, inst.max_signals_per_day,
                        )
                        continue

                inst_signals = await _evaluate_instrument(inst.symbol, news)
                for sig in inst_signals:
                    sig_dict = _signal_to_dict(sig)
                    if vix_regime == "high_fear":
                        sig_dict["confidence"] = max(0, sig_dict["confidence"] - 15)
                    all_signals.append(sig_dict)
                    new_count += 1
            except Exception as exc:
                logger.error("Auto-refresh error for %s: %s", inst.symbol, exc)

        # Correlation merge
        if config.correlation_merge_enabled and all_signals:
            all_signals = _merge_correlated_signals(all_signals)

        _cached_signals = all_signals
        _last_refresh_time = time.time()

        if new_count > 0:
            logger.info("Auto-refresh: %d new signal(s) generated", new_count)

        return new_count
