"""
Telegram Notifier
==================
Sends signal alerts and outcome notifications via Telegram Bot API.
Supports template-based rendering, notification rules, multi-chat,
quiet hours, cooldown, and batching.
Gracefully degrades — never blocks signal generation on Telegram failures.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Module-level singleton
_notifier: "TelegramNotifier | None" = None

# Cooldown tracker: key -> last_sent timestamp
_last_sent: dict[str, float] = {}

# Pause state (toggled by /pause /resume commands)
_is_paused: bool = False


class TelegramNotifier:
    """Telegram Bot API wrapper with rules engine and template-based sending."""

    def __init__(self, bot_token: str, chat_id: str, batch_window: int = 30):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.batch_window = batch_window
        self._signal_batch: list[dict] = []
        self._batch_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # --- Rule checks ---

    def _should_send_signal(self, signal: dict) -> bool:
        """Check notification rules before sending a signal alert."""
        from .templates import get_settings_store
        global _is_paused

        if _is_paused:
            return False

        settings = get_settings_store().get()
        instrument = signal.get("instrument", "")
        strategy = signal.get("strategy", "")
        confidence = signal.get("confidence", 0)

        # Instrument filter
        if not settings.instrument_notifications.get(instrument, True):
            return False

        # Strategy filter
        if not settings.strategy_notifications.get(strategy, True):
            return False

        # Min confidence
        if confidence < settings.min_confidence:
            return False

        # Quiet hours
        if self._is_quiet_hours(settings):
            logger.debug("Notification suppressed: quiet hours")
            return False

        # Cooldown
        if settings.cooldown_enabled and self._is_on_cooldown(instrument, settings):
            logger.debug("Notification suppressed: cooldown for %s", instrument)
            return False

        return True

    def _should_send_outcome(self, outcome: str) -> bool:
        """Check if outcome notifications are enabled for this outcome type."""
        from .templates import get_settings_store
        global _is_paused

        if _is_paused:
            return False

        settings = get_settings_store().get()
        if not settings.outcome_alerts:
            return False
        if outcome == "WIN" and not settings.outcome_win:
            return False
        if outcome == "LOSS" and not settings.outcome_loss:
            return False
        if outcome == "EXPIRED" and not settings.outcome_expired:
            return False
        return True

    def _is_quiet_hours(self, settings: Any) -> bool:
        """Check if current time is within quiet hours."""
        if not settings.quiet_hours_enabled:
            return False
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(settings.quiet_hours_timezone)
            now = datetime.now(tz)
            current_time = now.strftime("%H:%M")
            start = settings.quiet_hours_start
            end = settings.quiet_hours_end
            if start > end:  # overnight (23:00 - 07:00)
                return current_time >= start or current_time < end
            else:
                return start <= current_time < end
        except Exception:
            return False

    def _is_on_cooldown(self, instrument: str, settings: Any) -> bool:
        """Check if we recently sent a notification for this instrument."""
        key = f"signal:{instrument}"
        if key in _last_sent:
            elapsed = time.time() - _last_sent[key]
            if elapsed < settings.cooldown_hours * 3600:
                return True
        return False

    # --- Signal sending (batched, rule-checked) ---

    async def send_signal(self, signal: dict) -> None:
        """Queue a signal for batched sending (with rule checking)."""
        if not self._should_send_signal(signal):
            return

        async with self._lock:
            self._signal_batch.append(signal)
            if self._batch_task is None or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._send_signal_batch())

    async def _send_signal_batch(self) -> None:
        """Wait for batch window, then send using templates."""
        await asyncio.sleep(self.batch_window)

        async with self._lock:
            if not self._signal_batch:
                return
            batch = self._signal_batch.copy()
            self._signal_batch.clear()

        from .templates import get_template_store, get_settings_store, render_template

        settings = get_settings_store().get()
        store = get_template_store()

        try:
            if len(batch) == 1:
                template = store.get("signal_single")
                variables = self._build_signal_variables(batch[0])
            else:
                template = store.get("signal_batch")
                parts = []
                for sig in batch:
                    sv = self._build_signal_variables(sig, compact=True)
                    parts.append(sv.get("_compact_line", ""))
                variables = {
                    "signal_count": str(len(batch)),
                    "signals_list": "\n\n".join(parts),
                }

            if template is None:
                logger.error("Template not found for signal batch")
                return

            message = render_template(template.template, variables)
            await self._send_to_chats(message, settings.parse_mode)

            # Record cooldown
            for sig in batch:
                _last_sent[f"signal:{sig.get('instrument', '')}"] = time.time()

            logger.info("Sent %d signal(s) to Telegram", len(batch))
        except Exception as exc:
            logger.error("Failed to send signal batch to Telegram: %s", exc)

    # --- Outcome sending (template-based) ---

    async def send_outcome(self, signal: dict, outcome: str, pnl_pips: float | None = None) -> None:
        """Send an outcome notification when a signal resolves."""
        if not self._should_send_outcome(outcome):
            return

        from .templates import get_template_store, get_settings_store, render_template

        settings = get_settings_store().get()
        store = get_template_store()
        template = store.get(f"outcome_{outcome.lower()}")

        if template is None:
            template = store.get("outcome_expired")

        if template is None:
            logger.error("Template not found for outcome %s", outcome)
            return

        variables = self._build_outcome_variables(signal, outcome, pnl_pips)
        message = render_template(template.template, variables)

        try:
            await self._send_to_chats(message, settings.parse_mode)
            logger.info(
                "Sent outcome notification: %s %s -> %s",
                signal.get("instrument"), signal.get("direction"), outcome,
            )
        except Exception as exc:
            logger.error("Failed to send outcome to Telegram: %s", exc)

    # --- Custom message (for bot commands) ---

    async def send_custom(self, text: str, parse_mode: str = "markdown") -> bool:
        """Send a custom message (used by bot commands)."""
        try:
            await self._send_to_chats(text, parse_mode)
            return True
        except Exception as exc:
            logger.error("Custom message failed: %s", exc)
            return False

    async def send_test(self) -> bool:
        """Send a test message using the test template."""
        from .templates import get_template_store, get_settings_store, render_template

        settings = get_settings_store().get()
        store = get_template_store()
        template = store.get("test")
        message = render_template(template.template, {}) if template else "✅ *Macro Dashboard* notifier connected."
        try:
            await self._send_to_chats(message, settings.parse_mode)
            return True
        except Exception as exc:
            logger.error("Test message failed: %s", exc)
            return False

    # --- Variable builders ---

    def _build_signal_variables(self, signal: dict, compact: bool = False) -> dict[str, Any]:
        """Build template variables from a signal dict."""
        inst = signal.get("instrument", "???")
        direction = signal.get("direction", "???")

        from .templates import get_settings_store
        settings = get_settings_store().get()

        variables: dict[str, Any] = {
            "signal_ref": signal.get("signal_ref", ""),
            "direction_emoji": "🟢" if direction == "BUY" else "🔴",
            "instrument": inst,
            "direction": direction,
            "strategy": _display_name(signal.get("strategy", "???")),
            "confidence": str(signal.get("confidence", 0)),
            "entry": _format_price(signal.get("entry"), inst),
            "sl": _format_price(signal.get("stopLoss"), inst),
            "tp": _format_price(signal.get("takeProfit"), inst),
            "rr": str(signal.get("riskReward", 0)),
            "reasons": _sanitize_reasons(signal.get("reasons", [])[:3]),
            "tradingview_url": _tradingview_url(inst) if settings.tradingview_links else "",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        }

        if compact:
            ref = variables["signal_ref"]
            ref_str = f"{ref} " if ref else ""
            variables["_compact_line"] = (
                f"{variables['direction_emoji']} {ref_str}*{inst}* — {direction}\n"
                f"  Entry: `{variables['entry']}` → SL: `{variables['sl']}` → TP: `{variables['tp']}` | R:R: {variables['rr']}"
            )

        return variables

    def _build_outcome_variables(
        self, signal: dict, outcome: str, pnl_pips: float | None = None
    ) -> dict[str, Any]:
        """Build template variables for an outcome notification."""
        inst = signal.get("instrument", "???")
        direction = signal.get("direction", "???")
        notes = signal.get("notes", "")
        user_status = signal.get("userStatus", "auto")

        notes_line = f'\n_"' + notes[:100] + '"_' if notes else ""
        manual_line = ""
        if user_status == "taken":
            me = signal.get("manualEntry")
            mx = signal.get("manualExit")
            if me is not None:
                manual_line = f"\nEntry: `{_format_price(me, inst)}`"
            if mx is not None:
                manual_line += f" → Exit: `{_format_price(mx, inst)}`"

        return {
            "signal_ref": signal.get("signal_ref", ""),
            "instrument": inst,
            "direction": direction,
            "strategy": _display_name(signal.get("strategy", "???")),
            "pnl_pips": f"{pnl_pips:.1f}" if pnl_pips is not None else "",
            "pnl_sign": "+" if outcome == "WIN" else "",
            "notes_line": notes_line,
            "manual_line": manual_line,
        }

    # --- Core send ---

    async def _send_to_chats(self, text: str, parse_mode: str = "markdown") -> None:
        """Send a message to all enabled chats."""
        from .templates import get_settings_store
        settings = get_settings_store().get()

        chats = settings.chats
        # Fallback to primary chat_id if no chats configured
        if not any(c.get("id") for c in chats):
            await self._send_to_chat(self.chat_id, text, parse_mode)
            return

        for chat in chats:
            cid = str(chat.get("id", "")).strip()
            if chat.get("enabled") and cid and cid.lstrip("-").isdigit():
                try:
                    await self._send_to_chat(cid, text, parse_mode)
                except Exception as exc:
                    logger.error("Failed to send to chat %s: %s", chat.get("label", "?"), exc)

    async def _send_to_chat(self, chat_id: str, text: str, parse_mode: str = "markdown") -> None:
        """Send a message to a specific chat. Handles splitting if >4096 chars."""
        MAX_LENGTH = 4096

        chunks: list[str] = []
        while text:
            if len(text) <= MAX_LENGTH:
                chunks.append(text)
                break
            split_at = text.rfind("\n", 0, MAX_LENGTH)
            if split_at <= 0:
                split_at = MAX_LENGTH
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip("\n")

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": "",
            "disable_web_page_preview": True,
        }
        if parse_mode.lower() in ("markdown", "html"):
            payload["parse_mode"] = parse_mode.capitalize() if parse_mode.lower() == "html" else "Markdown"

        async with httpx.AsyncClient(timeout=10.0) as client:
            for chunk in chunks:
                payload["text"] = chunk
                try:
                    resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error("Telegram API error: %s", e.response.text)
                    raise
                except httpx.RequestError as e:
                    logger.error("Telegram request failed: %s", e)
                    raise

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


# --- Helper functions ---


def _display_name(name: str) -> str:
    """Convert snake_case to Title Case for Telegram display."""
    return name.replace("_", " ").title()


def _sanitize_reasons(reasons: list[str]) -> str:
    """Join reasons and remove characters that break Telegram Markdown."""
    text = ", ".join(reasons)
    return text.replace("_", " ")


_TV_MAP = {
    "XAUUSD": "OANDA:XAUUSD",
    "XAGUSD": "OANDA:XAGUSD",
    "USDJPY": "OANDA:USDJPY",
    "GBPJPY": "OANDA:GBPJPY",
    "BTCUSD": "BITSTAMP:BTCUSD",
}


def _tradingview_url(instrument: str) -> str:
    symbol = _TV_MAP.get(instrument, instrument)
    return f"[View Chart](https://www.tradingview.com/chart/?symbol={symbol})"


def _format_price(value: Any, instrument: str) -> str:
    try:
        price = float(value)
        if instrument in ("XAUUSD", "XAGUSD"):
            return f"{price:.2f}"
        elif instrument in ("USDJPY", "GBPJPY"):
            return f"{price:.3f}"
        elif instrument == "BTCUSD":
            return f"{price:,.0f}"
        else:
            return f"{price:.5f}"
    except (ValueError, TypeError):
        return str(value)


# --- Singleton getters ---

def get_notifier() -> "TelegramNotifier | None":
    return _notifier


def set_notifier(notifier: "TelegramNotifier | None") -> None:
    global _notifier
    _notifier = notifier
