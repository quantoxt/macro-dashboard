"""
Telegram Settings API
=====================
CRUD for notification settings, templates, test messages, and preview.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram")


# --- Settings ---


class SettingsUpdate(BaseModel):
    parse_mode: str | None = None
    batch_window: int | None = None
    outcome_alerts: bool | None = None
    outcome_win: bool | None = None
    outcome_loss: bool | None = None
    outcome_expired: bool | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    quiet_hours_timezone: str | None = None
    cooldown_enabled: bool | None = None
    cooldown_hours: float | None = None
    daily_summary_enabled: bool | None = None
    daily_summary_time: str | None = None
    tradingview_links: bool | None = None
    instrument_notifications: dict[str, bool] | None = None
    strategy_notifications: dict[str, bool] | None = None
    min_confidence: int | None = None
    chats: list[dict] | None = None


@router.get("/settings")
async def get_settings() -> Any:
    from dataclasses import asdict
    from notifier.templates import get_settings_store
    return asdict(get_settings_store().get())


@router.put("/settings")
async def update_settings(update: SettingsUpdate) -> dict[str, Any]:
    changes = update.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    from notifier.templates import get_settings_store
    settings = get_settings_store().update(**changes)
    return {"settings": settings}


# --- Templates ---


@router.get("/templates")
async def get_templates() -> dict[str, Any]:
    from notifier.templates import get_template_store
    store = get_template_store()
    return {
        "templates": {
            tid: {"id": t.id, "name": t.name, "template": t.template, "description": t.description}
            for tid, t in store.get_all().items()
        }
    }


class TemplateUpdate(BaseModel):
    template: str
    name: str | None = None


@router.put("/templates/{template_id}")
async def update_template(template_id: str, update: TemplateUpdate) -> dict[str, Any]:
    from notifier.templates import get_template_store
    store = get_template_store()
    try:
        t = store.update(template_id, update.template, name=update.name)
        return {"template": {"id": t.id, "name": t.name, "template": t.template, "description": t.description}}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/templates/{template_id}/reset")
async def reset_template(template_id: str) -> dict[str, Any]:
    from notifier.templates import get_template_store
    store = get_template_store()
    try:
        t = store.reset(template_id)
        return {"template": {"id": t.id, "name": t.name, "template": t.template, "description": t.description}}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Preview ---


class PreviewRequest(BaseModel):
    template_id: str
    variables: dict[str, Any]


@router.post("/preview")
async def preview_message(request: PreviewRequest) -> dict[str, Any]:
    from notifier.templates import get_template_store, render_template
    store = get_template_store()
    t = store.get(request.template_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")
    rendered = render_template(t.template, request.variables)
    return {"rendered": rendered}


# --- Test ---


class TestRequest(BaseModel):
    template_id: str = "test"
    variables: dict[str, Any] = {}


@router.post("/test")
async def send_test_message(request: TestRequest = TestRequest()) -> dict[str, Any]:
    from notifier.telegram import get_notifier
    from notifier.templates import get_template_store, render_template

    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")

    store = get_template_store()
    t = store.get(request.template_id) or store.get("test")
    if t is None:
        raise HTTPException(status_code=404, detail="Template not found")

    rendered = render_template(t.template, request.variables)
    success = await notifier.send_custom(rendered)
    return {"sent": success, "message": rendered}


# --- Status (replaces old /config/notifier) ---


@router.get("/status")
async def notifier_status() -> dict[str, Any]:
    from notifier.telegram import get_notifier
    notifier = get_notifier()
    if notifier is None:
        return {"enabled": False, "reason": "Not configured (missing env vars or disabled)"}
    return {
        "enabled": True,
        "configured": notifier.is_configured,
        "chatId": notifier.chat_id[:4] + "***" + notifier.chat_id[-4:],
        "batchWindow": notifier.batch_window,
    }


@router.post("/status/test")
async def notifier_test() -> dict[str, Any]:
    from notifier.telegram import get_notifier
    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")
    success = await notifier.send_test()
    return {"sent": success}


# --- Simulation endpoints ---


class SimSignalRequest(BaseModel):
    """Fake signal for testing the notification pipeline."""
    instrument: str = "XAUUSD"
    direction: str = "BUY"
    strategy: str = "confluence_breakout"
    confidence: int = 78
    entry: float = 2320.50
    stopLoss: float = 2310.00
    takeProfit: float = 2340.00
    riskReward: float = 1.95
    reasons: list[str] = [
        "H4 trend: BULLISH",
        "RSI at 45.2 — momentum room",
        "Confluence: 4 confirmations",
    ]
    timeframe: str = "H1"
    signal_ref: str = ""  # auto-generated if empty
    bypass_rules: bool = True  # skip quiet hours / cooldown for testing


@router.post("/test/signal")
async def simulate_signal_notification(request: SimSignalRequest = SimSignalRequest()) -> dict[str, Any]:
    """Send a fake signal notification through the full template + sending pipeline."""
    from notifier.telegram import get_notifier

    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")

    signal = request.model_dump()
    bypass = signal.pop("bypass_rules")

    # Auto-generate signal_ref if not provided
    if not signal.get("signal_ref"):
        from datetime import datetime, timezone
        from tracker.storage import SignalStorage
        storage = SignalStorage()
        count = storage.count_today() + 1
        signal["signal_ref"] = f"Signal {count}"

    if bypass:
        # Temporarily bypass quiet hours + cooldown
        from notifier.templates import get_settings_store
        settings = get_settings_store()
        original_quiet = settings.get().quiet_hours_enabled
        original_cooldown = settings.get().cooldown_enabled
        settings.update(quiet_hours_enabled=False, cooldown_enabled=False)

    try:
        await notifier.send_signal(signal)
        # Wait for batch window to flush
        import asyncio
        await asyncio.sleep(notifier.batch_window + 1)
        return {"sent": True, "signal": signal}
    finally:
        if bypass:
            settings.update(quiet_hours_enabled=original_quiet, cooldown_enabled=original_cooldown)


class SimOutcomeRequest(BaseModel):
    """Fake outcome for testing the outcome notification pipeline."""
    instrument: str = "XAUUSD"
    direction: str = "BUY"
    strategy: str = "mean_reversion"
    outcome: str = "WIN"  # WIN | LOSS | EXPIRED
    pnl_pips: float = 42.5
    signal_ref: str = "Signal 1"
    notes: str = ""
    userStatus: str = "auto"
    manualEntry: float | None = None
    manualExit: float | None = None
    bypass_rules: bool = True


@router.post("/test/outcome")
async def simulate_outcome_notification(request: SimOutcomeRequest = SimOutcomeRequest()) -> dict[str, Any]:
    """Send a fake outcome notification through the full template + sending pipeline."""
    from notifier.telegram import get_notifier

    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")

    signal = request.model_dump()
    outcome = signal.pop("outcome")
    pnl = signal.pop("pnl_pips")
    bypass = signal.pop("bypass_rules")

    if bypass:
        from notifier.templates import get_settings_store
        settings = get_settings_store()
        original_paused = settings.get().quiet_hours_enabled
        settings.update(quiet_hours_enabled=False)

    try:
        await notifier.send_outcome(signal, outcome, pnl)
        return {"sent": True, "outcome": outcome, "signal": signal}
    finally:
        if bypass:
            settings.update(quiet_hours_enabled=original_paused)


class SimBatchRequest(BaseModel):
    """Fake batch of signals for testing batch notification."""
    count: int = 3
    bypass_rules: bool = True


@router.post("/test/batch")
async def simulate_batch_notification(request: SimBatchRequest = SimBatchRequest()) -> dict[str, Any]:
    """Send multiple fake signals to test batch notification."""
    from notifier.telegram import get_notifier

    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")

    instruments = ["XAUUSD", "USDJPY", "BTCUSD"]
    strategies = ["confluence_breakout", "mean_reversion", "momentum_shift"]
    directions = ["BUY", "SELL"]

    signals = []
    for i in range(min(request.count, 5)):
        inst = instruments[i % len(instruments)]
        signals.append({
            "instrument": inst,
            "direction": directions[i % 2],
            "strategy": strategies[i % len(strategies)],
            "confidence": 65 + i * 5,
            "entry": 2300.0 + i * 100,
            "stopLoss": 2290.0 + i * 100,
            "takeProfit": 2320.0 + i * 100,
            "riskReward": 2.0,
            "reasons": ["Test reason 1", "Test reason 2"],
            "signal_ref": f"Signal {i + 1}",
        })

    if request.bypass_rules:
        from notifier.templates import get_settings_store
        settings = get_settings_store()
        original_quiet = settings.get().quiet_hours_enabled
        original_cooldown = settings.get().cooldown_enabled
        settings.update(quiet_hours_enabled=False, cooldown_enabled=False)

    try:
        for sig in signals:
            await notifier.send_signal(sig)

        import asyncio
        await asyncio.sleep(notifier.batch_window + 1)
        return {"sent": True, "count": len(signals), "signals": signals}
    finally:
        if request.bypass_rules:
            settings.update(quiet_hours_enabled=original_quiet, cooldown_enabled=original_cooldown)


# --- Subscriber management ---


@router.get("/subscribers")
async def list_subscribers() -> dict[str, Any]:
    """List all subscribers."""
    from dataclasses import asdict
    from notifier.subscribers import get_subscriber_store
    store = get_subscriber_store()
    return {
        "subscribers": [asdict(s) for s in store.get_all()],
        "active_count": store.get_count(),
        "total_count": len(store.get_all()),
    }


class RemoveSubscriberRequest(BaseModel):
    chat_id: str


@router.delete("/subscribers")
async def remove_subscriber(request: RemoveSubscriberRequest) -> dict[str, Any]:
    """Remove a subscriber permanently."""
    from notifier.subscribers import get_subscriber_store
    store = get_subscriber_store()
    success = store.hard_remove(request.chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"removed": True, "chat_id": request.chat_id}


class BroadcastRequest(BaseModel):
    message: str


@router.post("/broadcast")
async def api_broadcast(request: BroadcastRequest) -> dict[str, Any]:
    """Send broadcast to all subscribers."""
    from notifier.telegram import get_notifier
    from notifier.subscribers import get_subscriber_store

    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")

    store = get_subscriber_store()
    subscribers = store.get_all_active()

    if not subscribers:
        return {"sent": 0, "failed": 0, "total": 0}

    text = f"📢 *Broadcast*\n\n{request.message}"
    sent = 0
    failed = 0
    for sub in subscribers:
        try:
            await notifier._send_to_chat(sub.chat_id, text)
            sent += 1
        except Exception:
            failed += 1

    return {"sent": sent, "failed": failed, "total": len(subscribers)}
