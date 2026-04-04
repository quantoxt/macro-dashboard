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

# Max age for an active signal before it expires, by timeframe
MAX_ACTIVE_HOURS: dict[str, int] = {"H1": 8, "H4": 24, "D1": 48}
DEFAULT_MAX_ACTIVE_HOURS = 12

# If max adverse excursion exceeds this fraction of total risk, signal is expired
# even if SL wasn't hit — the trade thesis is broken
ADVERSE_EXPIRY_FRACTION = 0.80


class SignalTracker:
    """Tracks signal outcomes by checking live prices against TP/SL levels."""

    def __init__(self, storage: SignalStorage | None = None) -> None:
        self.storage = storage or SignalStorage()

    def track_signal(self, signal: Signal) -> TrackedSignal:
        """Save a new signal for tracking."""
        return self.storage.save_signal(signal)

    async def check_pending_signals(self) -> int:
        """Check all pending signals against current prices.

        Returns the number of signals resolved.
        """
        pending = self.storage.get_pending()
        if not pending:
            return 0

        # Group by instrument to minimize API calls
        by_instrument: dict[str, list[TrackedSignal]] = {}
        for ts in pending:
            by_instrument.setdefault(ts.instrument, []).append(ts)

        checked = 0
        config = get_config()

        for instrument, signals in by_instrument.items():
            try:
                inst = config.get_instrument(instrument)

                # Fetch latest H1 candle
                df = fetch_ohlc(inst.yahoo_ticker, "1h", 5)
                if df.empty:
                    continue

                current_high = df["high"].iloc[-1]
                current_low = df["low"].iloc[-1]
                current_close = df["close"].iloc[-1]

                for ts in signals:
                    resolved, outcome, pnl = self._check_signal(
                        ts, current_high, current_low, current_close, inst.pip_size
                    )
                    if resolved:
                        checked += 1

                        # Send outcome notification via Telegram
                        if config.notifier_outcome_alerts:
                            try:
                                from notifier.telegram import get_notifier
                                notifier = get_notifier()
                                if notifier is not None:
                                    sig_dict = {
                                        "instrument": ts.instrument,
                                        "direction": ts.direction,
                                        "strategy": ts.strategy,
                                        "riskReward": ts.risk_reward,
                                        "signal_ref": ts.signal_ref,
                                        "userStatus": ts.user_status,
                                        "notes": ts.notes,
                                        "manualEntry": ts.manual_entry,
                                        "manualExit": ts.manual_exit,
                                    }
                                    await notifier.send_outcome(sig_dict, outcome, pnl)
                            except Exception as exc:
                                logger.debug("Outcome notification failed: %s", exc)

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
    ) -> tuple[bool, str | None, float | None]:
        """Check a single signal against current price.

        Returns (resolved, outcome, pnl_pips).
        resolved is True if the signal was resolved (WIN/LOSS/EXPIRED).
        """
        now = datetime.now(timezone.utc)

        # --- Expiry checks (before TP/SL) ---

        # 1) Time-based expiry per timeframe
        try:
            gen_time = datetime.fromisoformat(ts.generated_at)
            max_hours = MAX_ACTIVE_HOURS.get(ts.timeframe, DEFAULT_MAX_ACTIVE_HOURS)
            if (now - gen_time) > timedelta(hours=max_hours):
                pnl = self._calc_pnl(ts, current_close, pip_size)
                self.storage.update_outcome(
                    ts.id,
                    outcome="EXPIRED",
                    exit_price=current_close,
                    exit_reason="EXPIRED_TIME",
                    pnl_pips=pnl,
                    max_favorable=ts.max_favorable,
                    max_adverse=ts.max_adverse,
                )
                logger.info(
                    "Signal expired (time): %s %s [%s, %dh old]",
                    ts.instrument, ts.direction, ts.timeframe, max_hours,
                )
                return True, "EXPIRED", pnl
        except (ValueError, TypeError):
            pass

        # 2) Adverse drift expiry — price moved past 80% of risk without hitting SL
        #    The trade thesis is broken even if SL wasn't tagged exactly.
        total_risk = abs(ts.entry - ts.stop_loss) / pip_size
        if total_risk > 0:
            adverse_pct = (ts.max_adverse or 0) / total_risk
            if adverse_pct >= ADVERSE_EXPIRY_FRACTION:
                pnl = self._calc_pnl(ts, current_close, pip_size)
                self.storage.update_outcome(
                    ts.id,
                    outcome="EXPIRED",
                    exit_price=current_close,
                    exit_reason="EXPIRED_ADVERSE",
                    pnl_pips=pnl,
                    max_favorable=ts.max_favorable,
                    max_adverse=ts.max_adverse,
                )
                logger.info(
                    "Signal expired (adverse drift %.0f%%): %s %s",
                    adverse_pct * 100, ts.instrument, ts.direction,
                )
                return True, "EXPIRED", pnl

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
                return True, "WIN", pnl
            else:
                exit_price = ts.stop_loss
                pnl = self._calc_pnl(ts, exit_price, pip_size)
                self.storage.update_outcome(
                    ts.id, "LOSS", exit_price, "STOP_LOSS", pnl
                )
                logger.info("Signal LOSS: %s %s (%.1f pips)", ts.instrument, ts.direction, pnl)
                return True, "LOSS", pnl

        return False, None, None

    def _calc_pnl(self, ts: TrackedSignal, exit_price: float, pip_size: float) -> float:
        """Calculate P&L in pips."""
        if ts.direction == "BUY":
            return (exit_price - ts.entry) / pip_size
        else:
            return (ts.entry - exit_price) / pip_size

    def get_strategy_performance(self, strategy_name: str, days: int = 30) -> dict:
        """Get performance stats for a specific strategy."""
        return self.storage.get_strategy_stats(strategy_name)
