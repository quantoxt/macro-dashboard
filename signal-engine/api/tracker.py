"""
Tracker API
============
GET /tracker/signals         — all tracked signals + stats
GET /tracker/signals/pending — unresolved signals
GET /tracker/performance     — per-strategy performance
GET /tracker/performance/{strategy} — single strategy performance
POST /tracker/check          — manually trigger a pending-signal check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tracker.storage import SignalStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracker")

# Shared storage instance — set during app startup
_storage: SignalStorage | None = None


def set_storage(storage: SignalStorage) -> None:
    global _storage
    _storage = storage


def get_storage() -> SignalStorage:
    global _storage
    if _storage is None:
        _storage = SignalStorage()
    return _storage


def _tracked_to_dict(ts: Any) -> dict[str, Any]:
    return {
        "id": ts.id,
        "instrument": ts.instrument,
        "direction": ts.direction,
        "confidence": ts.confidence,
        "entry": ts.entry,
        "stopLoss": ts.stop_loss,
        "takeProfit": ts.take_profit,
        "riskReward": ts.risk_reward,
        "strategy": ts.strategy,
        "timeframe": ts.timeframe,
        "reasons": ts.reasons,
        "generatedAt": ts.generated_at,
        "outcome": ts.outcome,
        "exitPrice": ts.exit_price,
        "exitReason": ts.exit_reason,
        "exitTime": ts.exit_time,
        "pnlPips": ts.pnl_pips,
        "maxFavorable": ts.max_favorable,
        "maxAdverse": ts.max_adverse,
        "userStatus": ts.user_status,
        "notes": ts.notes,
        "manualEntry": ts.manual_entry,
        "manualExit": ts.manual_exit,
    }


@router.get("/signals")
async def get_tracked_signals() -> dict[str, Any]:
    """All tracked signals with aggregate stats."""
    storage = get_storage()
    signals = storage.get_all()
    return {
        "signals": [_tracked_to_dict(s) for s in signals],
        "stats": storage.get_stats(),
    }


@router.get("/signals/pending")
async def get_pending_signals() -> dict[str, Any]:
    """Only unresolved signals."""
    storage = get_storage()
    pending = storage.get_pending()
    return {
        "signals": [_tracked_to_dict(s) for s in pending],
        "count": len(pending),
    }


@router.get("/performance")
async def get_performance() -> dict[str, Any]:
    """Per-strategy performance stats."""
    storage = get_storage()
    strategy_stats = storage.get_all_strategy_stats()
    overall = storage.get_stats()
    return {
        "strategies": strategy_stats,
        "overall": overall,
    }


@router.get("/performance/{strategy_name}")
async def get_strategy_performance(strategy_name: str) -> dict[str, Any]:
    """Detailed performance for one strategy."""
    storage = get_storage()
    stats = storage.get_strategy_stats(strategy_name)
    signals = [s for s in storage.get_all() if s.strategy == strategy_name]
    return {
        "strategy": strategy_name,
        "stats": stats,
        "signals": [_tracked_to_dict(s) for s in signals],
    }


@router.post("/check")
async def check_pending() -> dict[str, Any]:
    """Manually trigger a check of all pending signals."""
    from tracker.tracker import SignalTracker

    tracker = SignalTracker(get_storage())
    checked = await tracker.check_pending_signals()
    return {
        "checked": checked,
        "pendingRemaining": len(get_storage().get_pending()),
    }


class UpdateSignalRequest(BaseModel):
    """Request body for PUT /tracker/signals/{signal_id}."""
    user_status: str | None = None
    notes: str | None = None
    manual_entry: float | None = None
    manual_exit: float | None = None


@router.put("/signals/{signal_id}")
async def update_signal(signal_id: str, body: UpdateSignalRequest) -> dict[str, Any]:
    """Update user status, notes, or manual entry/exit on a tracked signal."""
    storage = get_storage()

    updates: dict[str, Any] = {}
    if body.user_status is not None:
        updates["user_status"] = body.user_status
    if body.notes is not None:
        updates["notes"] = body.notes
    if body.manual_entry is not None:
        updates["manual_entry"] = body.manual_entry
    if body.manual_exit is not None:
        updates["manual_exit"] = body.manual_exit

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated = storage.update_signal(signal_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if updated is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

    return {"signal": _tracked_to_dict(updated)}
