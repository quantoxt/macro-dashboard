"""
Telegram Bot Commands
======================
Handles incoming commands from Telegram users.
Public commands for everyone, owner commands restricted to configured chats.
Runs as a polling background task alongside the engine.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from notifier.templates import get_settings_store, get_template_store, render_template
from notifier.telegram import _is_paused, get_notifier

logger = logging.getLogger(__name__)

# Mutable module state for pause/resume
paused: bool = False


def is_paused() -> bool:
    return paused


async def register_bot_commands(notifier: Any) -> None:
    """Register bot commands with Telegram. Public commands for everyone, full set for owner's chat."""
    from .templates import get_settings_store

    public_commands = [
        {"command": "start", "description": "Subscribe to signals"},
        {"command": "subscribe", "description": "Subscribe to signals"},
        {"command": "unsubscribe", "description": "Unsubscribe from signals"},
        {"command": "signals", "description": "View active signals"},
        {"command": "status", "description": "Engine status"},
        {"command": "brief", "description": "Market overview"},
        {"command": "check", "description": "Check specific instrument"},
        {"command": "help", "description": "Show commands"},
    ]

    owner_commands = [
        *public_commands,
        {"command": "pause", "description": "Pause notifications"},
        {"command": "resume", "description": "Resume notifications"},
        {"command": "settings", "description": "View notification settings"},
        {"command": "history", "description": "Last 5 resolved signals"},
        {"command": "subscribers", "description": "View subscriber list"},
        {"command": "broadcast", "description": "Send message to all subscribers"},
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Default scope — public commands for everyone
            resp = await client.post(
                f"{notifier.base_url}/setMyCommands",
                json={"commands": public_commands},
            )
            resp.raise_for_status()
            logger.info("Registered %d public bot commands (default scope)", len(public_commands))

            # Owner's chat scope — full command set
            settings = get_settings_store().get()
            for chat in settings.chats:
                chat_id = str(chat.get("id", "")).strip()
                if chat.get("enabled") and chat_id.lstrip("-").isdigit():
                    resp = await client.post(
                        f"{notifier.base_url}/setMyCommands",
                        json={
                            "commands": owner_commands,
                            "scope": {"type": "chat", "chat_id": chat_id},
                        },
                    )
                    resp.raise_for_status()
                    logger.info("Registered %d owner commands for chat %s", len(owner_commands), chat_id)

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
                        await _handle_command(text, chat_id, message, notifier)

        except asyncio.CancelledError:
            break
        except httpx.TimeoutException:
            continue
        except httpx.HTTPStatusError as e:
            logger.warning("Bot polling HTTP error: %s", e.response.status_code)
            await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.warning("Bot command polling error: %s", e)
            await asyncio.sleep(poll_interval)


# --- Command routing ---


async def _handle_command(text: str, chat_id: int, message: dict, notifier: Any) -> None:
    """Route command — public commands for all, owner commands for authorized only."""
    settings = get_settings_store().get()
    is_owner = any(
        str(c.get("id", "")) == str(chat_id) and c.get("enabled")
        for c in settings.chats
    )

    command = text.split()[0].lower().split("@")[0]  # strip @botname
    args = text.split()[1:] if len(text.split()) > 1 else []

    # Check public commands first
    handler = PUBLIC_COMMANDS.get(command)
    if handler:
        try:
            await handler(args, chat_id, message, notifier)
        except Exception as e:
            logger.error("Command %s failed: %s", command, e)
            await notifier._send_to_chat(str(chat_id), f"Error running command: {e}")
        return

    # Check owner commands
    handler = OWNER_COMMANDS.get(command)
    if handler:
        if not is_owner:
            await notifier._send_to_chat(str(chat_id), "⚠ This command is restricted to the bot owner.")
            return
        try:
            await handler(args, chat_id, message, notifier)
        except Exception as e:
            logger.error("Command %s failed: %s", command, e)
            await notifier._send_to_chat(str(chat_id), f"Error running command: {e}")
        return

    # Unknown command
    await notifier._send_to_chat(str(chat_id), "Unknown command. Type /help for available commands.")


# --- Public command handlers ---


async def _cmd_start(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    """Welcome message + auto-subscribe."""
    from .subscribers import get_subscriber_store
    store = get_subscriber_store()
    chat_type = message.get("chat", {}).get("type", "private")

    if chat_type == "private":
        label = message.get("from", {}).get("first_name", "User")
    else:
        label = message.get("chat", {}).get("title", "Group")

    store.add(str(chat_id), chat_type, label)

    lines = [
        "👋 *Welcome to Macro Dashboard*\n",
        "You're now subscribed to signal notifications.",
        "You'll receive alerts when the engine generates trade signals.",
        "Use /unsubscribe to opt out anytime.",
    ]
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_subscribe(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    """Subscribe to signal notifications."""
    from .subscribers import get_subscriber_store
    store = get_subscriber_store()
    chat_type = message.get("chat", {}).get("type", "private")

    if chat_type == "private":
        label = message.get("from", {}).get("first_name", "User")
    else:
        label = message.get("chat", {}).get("title", "Group")

    was_new = not store.is_subscribed(str(chat_id))
    store.add(str(chat_id), chat_type, label)

    if was_new:
        await notifier._send_to_chat(str(chat_id), "✅ You're now subscribed to signal notifications.")
    else:
        await notifier._send_to_chat(str(chat_id), "You're already subscribed. ✅")


async def _cmd_unsubscribe(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    """Unsubscribe from signal notifications."""
    from .subscribers import get_subscriber_store
    store = get_subscriber_store()

    if store.remove(str(chat_id)):
        await notifier._send_to_chat(str(chat_id), "You've been unsubscribed. Use /subscribe to opt back in.")
    else:
        await notifier._send_to_chat(str(chat_id), "You're not subscribed.")


async def _cmd_signals(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    from api.signals import _cached_signals
    if not _cached_signals:
        await notifier._send_to_chat(str(chat_id), "No active signals right now.")
        return
    lines = [f"*Active Signals* ({len(_cached_signals)})\n"]
    for sig in _cached_signals:
        d = "🟢" if sig["direction"] == "BUY" else "🔴"
        ref = sig.get("signal_ref", "")
        ref_str = f"{ref} " if ref else ""
        lines.append(f"{d} {ref_str}*{sig['instrument']}* {sig['direction']} — {_display(sig['strategy'])}")
        lines.append(f"  Entry: `{sig['entry']}` → TP: `{sig['takeProfit']}` | R:R: {sig['riskReward']}")
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_status(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
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
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_brief(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
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
        msg = render_template(template.template, variables)
    else:
        msg = f"Session: {session} | VIX: {vix_val} | Active: {active} | Today: {today_count}"

    await notifier._send_to_chat(str(chat_id), msg)


async def _cmd_check(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    if not args:
        await notifier._send_to_chat(str(chat_id), "Usage: /check XAUUSD")
        return
    instrument = args[0].upper()
    from api.signals import _cached_signals

    matching = [s for s in _cached_signals if s["instrument"] == instrument]
    if not matching:
        await notifier._send_to_chat(str(chat_id), f"No active signals for {instrument}")
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
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_help(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    from .subscribers import get_subscriber_store
    store = get_subscriber_store()
    settings = get_settings_store().get()
    is_owner = any(str(c.get("id", "")) == str(chat_id) and c.get("enabled") for c in settings.chats)

    lines = [
        "*Macro Dashboard Bot*\n",
        "/subscribe — Get signal notifications",
        "/unsubscribe — Stop signal notifications",
        "/signals — View active signals",
        "/status — Engine status",
        "/brief — Market overview",
        "/check XAUUSD — Check specific instrument",
        "/help — Show this message",
    ]

    if is_owner:
        lines.extend([
            "\n*Owner Commands:*\n",
            "/pause — Pause notifications",
            "/resume — Resume notifications",
            "/settings — View notification settings",
            "/history — Last 5 resolved signals",
            "/subscribers — View subscriber list",
            "/broadcast MSG — Send message to all subscribers",
        ])

    if is_owner:
        sub_count = store.get_count()
        lines.append(f"\n📡 {sub_count} subscriber(s) active")

    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


# --- Owner command handlers ---


async def _cmd_pause(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    global paused
    paused = True
    await notifier._send_to_chat(str(chat_id), "Notifications *paused*. Use /resume to re-enable.")


async def _cmd_resume(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    global paused
    paused = False
    await notifier._send_to_chat(str(chat_id), "Notifications *resumed*.")


async def _cmd_settings(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
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
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_history(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    from tracker.storage import SignalStorage

    storage = SignalStorage()
    signals = [s for s in storage.get_all() if s.outcome is not None][-5:]
    if not signals:
        await notifier._send_to_chat(str(chat_id), "No signal history yet.")
        return
    lines = ["*Recent Signals*\n"]
    for s in reversed(signals):
        emoji = "✅" if s.outcome == "WIN" else ("❌" if s.outcome == "LOSS" else "⏰")
        ref = s.signal_ref or ""
        ref_str = f"{ref} " if ref else ""
        pnl = f" ({s.pnl_pips:+.1f} pips)" if s.pnl_pips is not None else ""
        lines.append(f"{emoji} {ref_str}{s.instrument} {s.direction} — {s.outcome}{pnl}")
    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


async def _cmd_subscribers(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    """Owner-only: View all subscribers."""
    from .subscribers import get_subscriber_store
    store = get_subscriber_store()
    all_subs = store.get_all()
    active = store.get_all_active()

    if not all_subs:
        await notifier._send_to_chat(str(chat_id), "No subscribers yet.")
        return

    lines = [f"*Subscribers* ({len(active)} active / {len(all_subs)} total)\n"]
    for s in all_subs:
        status = "✅" if s.active else "❌"
        chat_type_icon = "👤" if s.chat_type == "private" else "👥"
        lines.append(f"{status} {chat_type_icon} {s.label} (`{s.chat_id}`)")

    await notifier._send_to_chat(str(chat_id), "\n".join(lines))


# Broadcast rate limiting
_last_broadcast: float = 0
_BROADCAST_COOLDOWN: int = 0  # seconds (set > 0 to re-enable)


async def _cmd_broadcast(args: list[str], chat_id: int, message: dict, notifier: Any) -> None:
    """Owner-only: Send a custom message to all subscribers."""
    global _last_broadcast

    now = time.time()
    if now - _last_broadcast < _BROADCAST_COOLDOWN:
        remaining = int(_BROADCAST_COOLDOWN - (now - _last_broadcast))
        await notifier._send_to_chat(str(chat_id), f"⚠ Broadcast cooldown: wait {remaining}s")
        return

    if not args:
        await notifier._send_to_chat(str(chat_id), "Usage: /broadcast Your message here")
        return

    from .subscribers import get_subscriber_store
    store = get_subscriber_store()
    subscribers = store.get_all_active()

    if not subscribers:
        await notifier._send_to_chat(str(chat_id), "No active subscribers to broadcast to.")
        return

    text = " ".join(args)
    sent = 0
    failed = 0

    for sub in subscribers:
        try:
            await notifier._send_to_chat(sub.chat_id, f"📢 *Broadcast*\n\n{text}")
            sent += 1
        except Exception as e:
            logger.error("Broadcast to %s failed: %s", sub.chat_id, e)
            failed += 1

    _last_broadcast = time.time()
    await notifier._send_to_chat(
        str(chat_id),
        f"Broadcast sent: ✅ {sent} delivered, ❌ {failed} failed",
    )


# --- Command registries ---

PUBLIC_COMMANDS = {
    "/start": _cmd_start,
    "/subscribe": _cmd_subscribe,
    "/unsubscribe": _cmd_unsubscribe,
    "/signals": _cmd_signals,
    "/status": _cmd_status,
    "/brief": _cmd_brief,
    "/check": _cmd_check,
    "/help": _cmd_help,
}

OWNER_COMMANDS = {
    "/pause": _cmd_pause,
    "/resume": _cmd_resume,
    "/settings": _cmd_settings,
    "/history": _cmd_history,
    "/subscribers": _cmd_subscribers,
    "/broadcast": _cmd_broadcast,
}


# --- Helpers ---


def _display(name: str) -> str:
    """Convert snake_case to Title Case for Telegram display."""
    return name.replace("_", " ").title()
