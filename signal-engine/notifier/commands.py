"""
Telegram Bot Commands
======================
Handles incoming commands from Telegram users.
Runs as a polling background task alongside the engine.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from notifier.templates import get_settings_store, get_template_store, render_template
from notifier.telegram import _is_paused, get_notifier

logger = logging.getLogger(__name__)

# Mutable module state for pause/resume
paused: bool = False


def is_paused() -> bool:
    return paused


async def register_bot_commands(notifier: Any) -> None:
    """Register bot commands with Telegram so they appear in the / menu."""
    commands = [
        {"command": "signals", "description": "View active signals"},
        {"command": "status", "description": "Engine status"},
        {"command": "brief", "description": "Market overview"},
        {"command": "check", "description": "Check specific instrument"},
        {"command": "history", "description": "Last 5 resolved signals"},
        {"command": "settings", "description": "Notification settings"},
        {"command": "pause", "description": "Pause notifications"},
        {"command": "resume", "description": "Resume notifications"},
        {"command": "help", "description": "Show commands"},
    ]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{notifier.base_url}/setMyCommands",
                json={"commands": commands},
            )
            resp.raise_for_status()
            logger.info("Registered %d bot commands with Telegram", len(commands))
    except Exception as e:
        logger.warning("Failed to register bot commands: %s", e)


async def poll_for_updates(poll_interval: int = 2) -> None:
    """Long-poll for Telegram updates. Runs as a background task."""
    notifier = get_notifier()
    if notifier is None:
        logger.info("Bot commands disabled: notifier not configured")
        return

    offset = 0

    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{notifier.base_url}/getUpdates",
                    json={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                )
                resp.raise_for_status()
                data = resp.json()

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")

                    if text.startswith("/"):
                        await _handle_command(text, chat_id, notifier)

        except asyncio.CancelledError:
            break
        except httpx.TimeoutException:
            # Normal — long poll timed out, just retry
            continue
        except httpx.HTTPStatusError as e:
            logger.warning("Bot polling HTTP error: %s", e.response.status_code)
            await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.warning("Bot command polling error: %s", e)
            await asyncio.sleep(poll_interval)


async def _handle_command(text: str, chat_id: int, notifier: Any) -> None:
    """Route a bot command to its handler."""
    settings = get_settings_store().get()
    authorized = any(
        str(c.get("id", "")) == str(chat_id) and c.get("enabled")
        for c in settings.chats
    )
    if not authorized:
        return

    command = text.split()[0].lower().split("@")[0]  # strip @botname
    args = text.split()[1:] if len(text.split()) > 1 else []

    handlers = {
        "/signals": _cmd_signals,
        "/status": _cmd_status,
        "/pause": _cmd_pause,
        "/resume": _cmd_resume,
        "/settings": _cmd_settings,
        "/history": _cmd_history,
        "/check": _cmd_check,
        "/brief": _cmd_brief,
        "/help": _cmd_help,
    }

    handler = handlers.get(command)
    if handler:
        try:
            await handler(args, chat_id, notifier)
        except Exception as e:
            logger.error("Command %s failed: %s", command, e)
            await notifier._send_to_chat(chat_id, f"Error running command: {e}")
    else:
        await notifier._send_to_chat(chat_id, "Unknown command. Type /help for available commands.")


# --- Command handlers ---


def _display(name: str) -> str:
    """Convert snake_case to Title Case for Telegram display."""
    return name.replace("_", " ").title()


async def _cmd_signals(args: list[str], chat_id: int, notifier: Any) -> None:
    from api.signals import _cached_signals
    if not _cached_signals:
        await notifier._send_to_chat(chat_id, "No active signals right now.")
        return
    lines = [f"*Active Signals* ({len(_cached_signals)})\n"]
    for sig in _cached_signals:
        d = "🟢" if sig["direction"] == "BUY" else "🔴"
        ref = sig.get("signal_ref", "")
        ref_str = f"{ref} " if ref else ""
        lines.append(f"{d} {ref_str}*{sig['instrument']}* {sig['direction']} — {_display(sig['strategy'])}")
        lines.append(f"  Entry: `{sig['entry']}` → TP: `{sig['takeProfit']}` | R:R: {sig['riskReward']}")
    await notifier._send_to_chat(chat_id, "\n".join(lines))


async def _cmd_status(args: list[str], chat_id: int, notifier: Any) -> None:
    from api.signals import _cached_signals, _last_refresh_time
    from indicators.vix import get_vix_cache_status

    vix = get_vix_cache_status()
    age = int(time.time() - _last_refresh_time) if _last_refresh_time else 0
    lines = [
        "*Engine Status*\n",
        f"VIX: {vix.get('vix', '?')} ({'cached' if vix.get('cached') else 'uncached'})",
        f"Active signals: {len(_cached_signals)}",
        f"Last refresh: {age}s ago",
        f"Notifier: {'paused' if paused else 'active'}",
    ]
    await notifier._send_to_chat(chat_id, "\n".join(lines))


async def _cmd_pause(args: list[str], chat_id: int, notifier: Any) -> None:
    global paused
    paused = True
    await notifier._send_to_chat(chat_id, "Notifications *paused*. Use /resume to re-enable.")


async def _cmd_resume(args: list[str], chat_id: int, notifier: Any) -> None:
    global paused
    paused = False
    await notifier._send_to_chat(chat_id, "Notifications *resumed*.")


async def _cmd_settings(args: list[str], chat_id: int, notifier: Any) -> None:
    settings = get_settings_store().get()
    lines = [
        "*Notification Settings*\n",
        f"Batch window: {settings.batch_window}s",
        f"Min confidence: {settings.min_confidence}%",
        f"Outcome alerts: {'on' if settings.outcome_alerts else 'off'}",
        f"Quiet hours: {'on' if settings.quiet_hours_enabled else 'off'} "
        f"({settings.quiet_hours_start} - {settings.quiet_hours_end})",
        f"Cooldown: {'on' if settings.cooldown_enabled else 'off'} ({settings.cooldown_hours}h)",
        f"TradingView links: {'on' if settings.tradingview_links else 'off'}",
    ]
    inst_lines = [f"  {'✅' if v else '❌'} {k}" for k, v in settings.instrument_notifications.items()]
    lines.append("\n*Instruments:*")
    lines.extend(inst_lines)
    await notifier._send_to_chat(chat_id, "\n".join(lines))


async def _cmd_history(args: list[str], chat_id: int, notifier: Any) -> None:
    from tracker.storage import SignalStorage

    storage = SignalStorage()
    signals = [s for s in storage.get_all() if s.outcome is not None][-5:]
    if not signals:
        await notifier._send_to_chat(chat_id, "No signal history yet.")
        return
    lines = ["*Recent Signals*\n"]
    for s in reversed(signals):
        emoji = "✅" if s.outcome == "WIN" else ("❌" if s.outcome == "LOSS" else "⏰")
        ref = s.signal_ref or ""
        ref_str = f"{ref} " if ref else ""
        pnl = f" ({s.pnl_pips:+.1f} pips)" if s.pnl_pips is not None else ""
        lines.append(f"{emoji} {ref_str}{s.instrument} {s.direction} — {s.outcome}{pnl}")
    await notifier._send_to_chat(chat_id, "\n".join(lines))


async def _cmd_check(args: list[str], chat_id: int, notifier: Any) -> None:
    if not args:
        await notifier._send_to_chat(chat_id, "Usage: /check XAUUSD")
        return
    instrument = args[0].upper()
    from api.signals import _cached_signals

    matching = [s for s in _cached_signals if s["instrument"] == instrument]
    if not matching:
        await notifier._send_to_chat(chat_id, f"No active signals for {instrument}")
        return
    lines = [f"*{instrument}*\n"]
    for sig in matching:
        d = "🟢" if sig["direction"] == "BUY" else "🔴"
        ref = sig.get("signal_ref", "")
        ref_str = f"{ref} " if ref else ""
        lines.append(f"{d} {ref_str}{sig['direction']} ({_display(sig['strategy'])}) — {sig['confidence']}% confidence")
        lines.append(f"  Entry: `{sig['entry']}` → SL: `{sig['stopLoss']}` → TP: `{sig['takeProfit']}`")
        reasons_text = ", ".join(sig.get("reasons", [])[:2]).replace("_", " ")
        lines.append(f"  R:R: {sig['riskReward']} | {reasons_text}")
    await notifier._send_to_chat(chat_id, "\n".join(lines))


async def _cmd_brief(args: list[str], chat_id: int, notifier: Any) -> None:
    from indicators.news import get_current_session
    from api.signals import _cached_signals

    session = get_current_session()
    active = len(_cached_signals)

    from tracker.storage import SignalStorage
    storage = SignalStorage()
    all_s = storage.get_all()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = sum(1 for s in all_s if s.generated_at.startswith(today))

    try:
        from indicators.vix import get_vix_cache_status
        vix = get_vix_cache_status()
        vix_val = vix.get("vix", "?")
    except Exception:
        vix_val = "?"

    store = get_template_store()
    template = store.get("brief")
    variables = {
        "session": session,
        "vix": str(vix_val),
        "vix_regime": "normal",
        "active_signals": str(active),
        "today_signals": str(today_count),
    }

    if template:
        message = render_template(template.template, variables)
    else:
        message = f"Session: {session} | VIX: {vix_val} | Active: {active} | Today: {today_count}"

    await notifier._send_to_chat(chat_id, message)


async def _cmd_help(args: list[str], chat_id: int, notifier: Any) -> None:
    lines = [
        "*Available Commands*\n",
        "/signals — View active signals",
        "/status — Engine status",
        "/brief — Market overview",
        "/check XAUUSD — Check specific instrument",
        "/history — Last 5 resolved signals",
        "/settings — View notification settings",
        "/pause — Pause notifications",
        "/resume — Resume notifications",
        "/help — Show this message",
    ]
    await notifier._send_to_chat(chat_id, "\n".join(lines))
