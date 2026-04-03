"""
Signal Storage — JSON File Persistence
========================================
Stores tracked signals and their outcomes in a JSON file.
Simple, no database needed for Phase 4.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from strategies.base import Signal

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SIGNALS_FILE = DATA_DIR / "signals.json"

MAX_AGE_DAYS = 30


@dataclass
class TrackedSignal:
    """A signal being tracked for outcome."""
    id: str
    instrument: str
    direction: str
    confidence: int
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    strategy: str
    timeframe: str
    reasons: list[str]
    generated_at: str
    outcome: str | None = None       # "WIN" | "LOSS" | "EXPIRED" | None (pending)
    exit_price: float | None = None
    exit_reason: str | None = None    # "TAKE_PROFIT" | "STOP_LOSS" | "EXPIRED"
    exit_time: str | None = None
    pnl_pips: float | None = None
    max_favorable: float | None = None
    max_adverse: float | None = None
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TrackedSignal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SignalStorage:
    """JSON-file-backed storage for tracked signals."""

    def __init__(self, path: Path = SIGNALS_FILE) -> None:
        self._path = path
        self._signals: dict[str, TrackedSignal] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for item in data:
                ts = TrackedSignal.from_dict(item)
                self._signals[ts.id] = ts
            logger.info("Loaded %d tracked signals", len(self._signals))
        except Exception as exc:
            logger.warning("Failed to load signals: %s", exc)

    def _save(self) -> None:
        try:
            data = [ts.to_dict() for ts in self._signals.values()]
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed to save signals: %s", exc)

    def _cleanup_old(self) -> None:
        """Remove signals older than MAX_AGE_DAYS."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (MAX_AGE_DAYS * 86400)
        to_remove = []
        for sid, ts in self._signals.items():
            try:
                gen_time = datetime.fromisoformat(ts.generated_at).timestamp()
                if gen_time < cutoff:
                    to_remove.append(sid)
            except (ValueError, TypeError):
                pass
        for sid in to_remove:
            del self._signals[sid]
        if to_remove:
            logger.info("Cleaned up %d old signals", len(to_remove))

    def save_signal(self, signal: Signal) -> TrackedSignal:
        """Convert a live Signal to a TrackedSignal and persist it."""
        ts = TrackedSignal(
            id=str(uuid.uuid4()),
            instrument=signal.instrument,
            direction=signal.direction,
            confidence=signal.confidence,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_reward=signal.risk_reward,
            strategy=signal.strategy,
            timeframe=signal.timeframe,
            reasons=signal.reasons,
            generated_at=signal.generated_at,
        )
        self._signals[ts.id] = ts
        self._save()
        logger.debug("Tracked signal: %s %s %s", ts.strategy, ts.instrument, ts.direction)
        return ts

    def update_outcome(
        self,
        signal_id: str,
        outcome: str,
        exit_price: float,
        exit_reason: str,
        pnl_pips: float | None = None,
        max_favorable: float | None = None,
        max_adverse: float | None = None,
    ) -> None:
        """Update a tracked signal with its outcome."""
        ts = self._signals.get(signal_id)
        if ts is None:
            return

        self._signals[signal_id] = TrackedSignal(
            id=ts.id,
            instrument=ts.instrument,
            direction=ts.direction,
            confidence=ts.confidence,
            entry=ts.entry,
            stop_loss=ts.stop_loss,
            take_profit=ts.take_profit,
            risk_reward=ts.risk_reward,
            strategy=ts.strategy,
            timeframe=ts.timeframe,
            reasons=ts.reasons,
            generated_at=ts.generated_at,
            outcome=outcome,
            exit_price=round(exit_price, 5),
            exit_reason=exit_reason,
            exit_time=datetime.now(timezone.utc).isoformat(),
            pnl_pips=round(pnl_pips, 2) if pnl_pips is not None else None,
            max_favorable=round(max_favorable, 5) if max_favorable is not None else ts.max_favorable,
            max_adverse=round(max_adverse, 5) if max_adverse is not None else ts.max_adverse,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save()

    def update_excursions(
        self,
        signal_id: str,
        max_favorable: float | None = None,
        max_adverse: float | None = None,
    ) -> None:
        """Update max favorable/adverse without resolving the signal."""
        ts = self._signals.get(signal_id)
        if ts is None:
            return

        # Only update if the new value is more extreme
        mf = max_favorable
        if mf is not None and ts.max_favorable is not None:
            mf = max(mf, ts.max_favorable)
        elif ts.max_favorable is not None:
            mf = ts.max_favorable

        ma = max_adverse
        if ma is not None and ts.max_adverse is not None:
            ma = max(ma, ts.max_adverse)
        elif ts.max_adverse is not None:
            ma = ts.max_adverse

        self._signals[signal_id] = TrackedSignal(
            id=ts.id,
            instrument=ts.instrument,
            direction=ts.direction,
            confidence=ts.confidence,
            entry=ts.entry,
            stop_loss=ts.stop_loss,
            take_profit=ts.take_profit,
            risk_reward=ts.risk_reward,
            strategy=ts.strategy,
            timeframe=ts.timeframe,
            reasons=ts.reasons,
            generated_at=ts.generated_at,
            outcome=ts.outcome,
            exit_price=ts.exit_price,
            exit_reason=ts.exit_reason,
            exit_time=ts.exit_time,
            pnl_pips=ts.pnl_pips,
            max_favorable=mf,
            max_adverse=ma,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save()

    def get_pending(self) -> list[TrackedSignal]:
        return [ts for ts in self._signals.values() if ts.outcome is None]

    def get_resolved(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> list[TrackedSignal]:
        resolved = [ts for ts in self._signals.values() if ts.outcome is not None]
        if start_date:
            resolved = [ts for ts in resolved if ts.generated_at >= start_date]
        if end_date:
            resolved = [ts for ts in resolved if ts.generated_at <= end_date]
        return resolved

    def get_all(self) -> list[TrackedSignal]:
        return list(self._signals.values())

    def get_by_id(self, signal_id: str) -> TrackedSignal | None:
        return self._signals.get(signal_id)

    def get_stats(self) -> dict[str, Any]:
        all_s = list(self._signals.values())
        pending = [s for s in all_s if s.outcome is None]
        wins = [s for s in all_s if s.outcome == "WIN"]
        losses = [s for s in all_s if s.outcome == "LOSS"]
        expired = [s for s in all_s if s.outcome == "EXPIRED"]

        total_pnl = sum(s.pnl_pips or 0 for s in all_s)

        return {
            "total": len(all_s),
            "wins": len(wins),
            "losses": len(losses),
            "expired": len(expired),
            "pending": len(pending),
            "winRate": round(len(wins) / max(len(wins) + len(losses), 1), 4),
            "totalPnlPips": round(total_pnl, 2),
        }

    def get_strategy_stats(self, strategy_name: str) -> dict[str, Any]:
        """Get stats for a specific strategy."""
        all_s = [s for s in self._signals.values() if s.strategy == strategy_name]
        return self._calc_strategy_stats(all_s)

    def get_all_strategy_stats(self) -> dict[str, dict[str, Any]]:
        """Get per-strategy stats."""
        from collections import defaultdict
        grouped: dict[str, list[TrackedSignal]] = defaultdict(list)
        for s in self._signals.values():
            grouped[s.strategy].append(s)

        return {
            name: self._calc_strategy_stats(signals)
            for name, signals in grouped.items()
        }

    def _calc_strategy_stats(self, signals: list[TrackedSignal]) -> dict[str, Any]:
        if not signals:
            return {
                "total": 0, "wins": 0, "losses": 0, "expired": 0, "pending": 0,
                "winRate": 0.0, "avgPnlPips": 0.0, "totalPnlPips": 0.0,
                "bestTrade": 0.0, "worstTrade": 0.0,
            }

        wins = [s for s in signals if s.outcome == "WIN"]
        losses = [s for s in signals if s.outcome == "LOSS"]
        expired = [s for s in signals if s.outcome == "EXPIRED"]
        pending = [s for s in signals if s.outcome is None]
        resolved = wins + losses

        total_pnl = sum(s.pnl_pips or 0 for s in signals)
        pips = [s.pnl_pips for s in resolved if s.pnl_pips is not None]

        return {
            "total": len(signals),
            "wins": len(wins),
            "losses": len(losses),
            "expired": len(expired),
            "pending": len(pending),
            "winRate": round(len(wins) / max(len(resolved), 1), 4),
            "avgPnlPips": round(total_pnl / max(len(resolved), 1), 2),
            "totalPnlPips": round(total_pnl, 2),
            "bestTrade": round(max(pips), 2) if pips else 0.0,
            "worstTrade": round(min(pips), 2) if pips else 0.0,
        }
