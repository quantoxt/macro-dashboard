"""
Signal Outcome Tracker
=======================
Checks pending tracked signals against live price to determine outcomes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from config import get_config
from data.fetcher import fetch_ohlc
from tracker.storage import SignalStorage, TrackedSignal
from strategies.base import Signal

logger = logging.getLogger(__name__)

# Max age for a pending signal before it expires (hours)
MAX_PENDING_HOURS = 48


class SignalTracker:
    """Tracks signal outcomes by checking live prices against TP/SL levels."""

    def __init__(self, storage: SignalStorage | None = None) -> None:
        self.storage = storage or SignalStorage()

    def track_signal(self, signal: Signal) -> TrackedSignal:
        """Save a new signal for tracking."""
        return self.storage.save_signal(signal)

    async def check_pending_signals(self) -> int:
        """Check all pending signals against current prices.

        Returns the number of signals checked.
        """
        pending = self.storage.get_pending()
        if not pending:
            return 0

        # Group by instrument to minimize API calls
        by_instrument: dict[str, list[TrackedSignal]] = {}
        for ts in pending:
            by_instrument.setdefault(ts.instrument, []).append(ts)

        checked = 0

        for instrument, signals in by_instrument.items():
            try:
                config = get_config()
                inst = config.get_instrument(instrument)

                # Fetch latest H1 candle
                df = fetch_ohlc(inst.yahoo_ticker, "1h", 5)
                if df.empty:
                    continue

                current_high = df["high"].iloc[-1]
                current_low = df["low"].iloc[-1]
                current_close = df["close"].iloc[-1]

                for ts in signals:
                    resolved = self._check_signal(
                        ts, current_high, current_low, current_close, inst.pip_size
                    )
                    if resolved:
                        checked += 1

            except Exception as exc:
                logger.error("Tracker check failed for %s: %s", instrument, exc)

        return checked

    def _check_signal(
        self,
        ts: TrackedSignal,
        current_high: float,
        current_low: float,
        current_close: float,
        pip_size: float,
    ) -> bool:
        """Check a single signal against current price.

        Returns True if the signal was resolved (WIN/LOSS/EXPIRED).
        """
        now = datetime.now(timezone.utc)

        # Check expiration first
        try:
            gen_time = datetime.fromisoformat(ts.generated_at)
            if (now - gen_time) > timedelta(hours=MAX_PENDING_HOURS):
                pnl = self._calc_pnl(ts, current_close, pip_size)
                self.storage.update_outcome(
                    ts.id,
                    outcome="EXPIRED",
                    exit_price=current_close,
                    exit_reason="EXPIRED",
                    pnl_pips=pnl,
                    max_favorable=ts.max_favorable,
                    max_adverse=ts.max_adverse,
                )
                logger.info("Signal expired: %s %s", ts.instrument, ts.direction)
                return True
        except (ValueError, TypeError):
            pass

        # Check TP/SL hit
        hit_tp = False
        hit_sl = False

        if ts.direction == "BUY":
            hit_tp = current_high >= ts.take_profit
            hit_sl = current_low <= ts.stop_loss
        else:  # SELL
            hit_tp = current_low <= ts.take_profit
            hit_sl = current_high >= ts.stop_loss

        # Update max favorable/adverse excursions
        if ts.direction == "BUY":
            favorable = (current_high - ts.entry) / pip_size
            adverse = (ts.entry - current_low) / pip_size
        else:
            favorable = (ts.entry - current_low) / pip_size
            adverse = (current_high - ts.entry) / pip_size

        self.storage.update_excursions(ts.id, max_favorable=favorable, max_adverse=adverse)

        if hit_tp or hit_sl:
            if hit_tp and hit_sl:
                # Both hit — determine which is closer (more likely hit first)
                tp_dist = abs(ts.take_profit - ts.entry)
                sl_dist = abs(ts.stop_loss - ts.entry)
                if sl_dist <= tp_dist:
                    hit_tp = False
                else:
                    hit_sl = False

            if hit_tp:
                exit_price = ts.take_profit
                pnl = self._calc_pnl(ts, exit_price, pip_size)
                self.storage.update_outcome(
                    ts.id, "WIN", exit_price, "TAKE_PROFIT", pnl
                )
                logger.info("Signal WIN: %s %s (+%.1f pips)", ts.instrument, ts.direction, pnl)
            else:
                exit_price = ts.stop_loss
                pnl = self._calc_pnl(ts, exit_price, pip_size)
                self.storage.update_outcome(
                    ts.id, "LOSS", exit_price, "STOP_LOSS", pnl
                )
                logger.info("Signal LOSS: %s %s (%.1f pips)", ts.instrument, ts.direction, pnl)

            return True

        return False

    def _calc_pnl(self, ts: TrackedSignal, exit_price: float, pip_size: float) -> float:
        """Calculate P&L in pips."""
        if ts.direction == "BUY":
            return (exit_price - ts.entry) / pip_size
        else:
            return (ts.entry - exit_price) / pip_size

    def get_strategy_performance(self, strategy_name: str, days: int = 30) -> dict:
        """Get performance stats for a specific strategy."""
        return self.storage.get_strategy_stats(strategy_name)
