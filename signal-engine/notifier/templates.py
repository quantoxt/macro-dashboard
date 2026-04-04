"""
Message Template System & Notification Settings
=================================================
Stores message templates and notification settings with JSON persistence.
Templates use {variable} syntax. Unknown variables render as empty string.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_FILE = DATA_DIR / "telegram-templates.json"
SETTINGS_FILE = DATA_DIR / "telegram-settings.json"

# --- Default Templates ---

DEFAULT_TEMPLATES = {
    "signal_single": {
        "name": "Signal Alert (Single)",
        "description": "Sent when a single new signal is generated",
        "template": (
            "🚨 *New Signal* {signal_ref}\n\n"
            "{direction_emoji} *{instrument}* — {direction}\n"
            "Strategy: {strategy}\n"
            "Confidence: {confidence}%\n\n"
            "Entry: `{entry}` → SL: `{sl}` → TP: `{tp}`\n"
            "R:R: {rr}\n\n"
            "_{reasons}_\n"
            "{tradingview_url}"
        ),
    },
    "signal_batch": {
        "name": "Signal Alert (Batch)",
        "description": "Sent when multiple signals are generated in the same cycle",
        "template": "🚨 *{signal_count} New Signals*\n\n{signals_list}",
    },
    "outcome_win": {
        "name": "Outcome: Win",
        "description": "Sent when a signal hits take profit",
        "template": (
            "✅ {signal_ref} *{instrument}* {direction} ({strategy}) → *WIN* {pnl_sign}{pnl_pips} pips\n"
            "{notes_line}"
            "{manual_line}"
        ),
    },
    "outcome_loss": {
        "name": "Outcome: Loss",
        "description": "Sent when a signal hits stop loss",
        "template": (
            "❌ {signal_ref} *{instrument}* {direction} ({strategy}) → *LOSS* {pnl_pips} pips\n"
            "{notes_line}"
            "{manual_line}"
        ),
    },
    "outcome_expired": {
        "name": "Outcome: Expired",
        "description": "Sent when a signal expires without hitting TP/SL",
        "template": "⏰ {signal_ref} *{instrument}* {direction} ({strategy}) → *EXPIRED*",
    },
    "daily_summary": {
        "name": "Daily Summary",
        "description": "Scheduled daily summary of signal performance",
        "template": (
            "📊 *Daily Summary*\n\n"
            "Total signals: {total_signals}\n"
            "Wins: {wins} | Losses: {losses} | Expired: {expired}\n"
            "Win rate: {win_rate}%\n"
            "Avg PnL: {avg_pnl} pips\n\n"
            "_{top_performers}_"
        ),
    },
    "brief": {
        "name": "Market Brief",
        "description": "Quick market overview triggered by /brief command",
        "template": (
            "📋 *Market Brief*\n\n"
            "Session: {session}\n"
            "VIX: {vix} ({vix_regime})\n"
            "Active signals: {active_signals}\n"
            "Today's signals: {today_signals}"
        ),
    },
    "test": {
        "name": "Test Message",
        "description": "Sent when testing the bot connection",
        "template": "✅ *Macro Dashboard* notifier is connected and working.",
    },
}


@dataclass
class MessageTemplate:
    id: str
    name: str
    template: str
    description: str = ""


class TemplateStore:
    """Manages message templates with JSON persistence."""

    def __init__(self) -> None:
        self._templates: dict[str, MessageTemplate] = {}
        self._load()

    def _load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if TEMPLATES_FILE.exists():
            try:
                with open(TEMPLATES_FILE) as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    self._templates[tid] = MessageTemplate(
                        id=tid,
                        name=tdata.get("name", tid),
                        template=tdata.get("template", ""),
                        description=tdata.get("description", ""),
                    )
                logger.info("Loaded %d templates from file", len(self._templates))
                return
            except Exception as e:
                logger.error("Failed to load templates: %s", e)

        # Load defaults
        for tid, tdata in DEFAULT_TEMPLATES.items():
            self._templates[tid] = MessageTemplate(id=tid, **tdata)
        self._save()
        logger.info("Initialized %d default templates", len(self._templates))

    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {tid: asdict(t) for tid, t in self._templates.items()}
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def get(self, template_id: str) -> MessageTemplate | None:
        return self._templates.get(template_id)

    def get_all(self) -> dict[str, MessageTemplate]:
        return dict(self._templates)

    def update(self, template_id: str, template: str, name: str | None = None) -> MessageTemplate:
        if template_id not in self._templates:
            raise ValueError(f"Unknown template: {template_id}")
        t = self._templates[template_id]
        t = MessageTemplate(
            id=template_id,
            name=name or t.name,
            template=template,
            description=t.description,
        )
        self._templates[template_id] = t
        self._save()
        return t

    def reset(self, template_id: str) -> MessageTemplate:
        if template_id not in DEFAULT_TEMPLATES:
            raise ValueError(f"Unknown template: {template_id}")
        tdata = DEFAULT_TEMPLATES[template_id]
        t = MessageTemplate(id=template_id, **tdata)
        self._templates[template_id] = t
        self._save()
        return t


# --- Settings ---


@dataclass
class TelegramSettings:
    parse_mode: str = "markdown"
    batch_window: int = 30
    outcome_alerts: bool = True
    outcome_win: bool = True
    outcome_loss: bool = True
    outcome_expired: bool = False
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "23:00"
    quiet_hours_end: str = "07:00"
    quiet_hours_timezone: str = "Africa/Lagos"
    cooldown_enabled: bool = True
    cooldown_hours: float = 2.0
    daily_summary_enabled: bool = False
    daily_summary_time: str = "08:00"
    tradingview_links: bool = True
    instrument_notifications: dict[str, bool] = field(default_factory=lambda: {
        "XAUUSD": True, "XAGUSD": True,
        "USDJPY": True, "GBPJPY": True, "BTCUSD": True,
    })
    strategy_notifications: dict[str, bool] = field(default_factory=lambda: {
        "confluence_breakout": True,
        "mean_reversion": True,
        "momentum_shift": True,
    })
    min_confidence: int = 0
    chats: list[dict] = field(default_factory=lambda: [
        {"id": "", "label": "Primary", "enabled": True}
    ])


class SettingsStore:
    """Manages Telegram notification settings with JSON persistence."""

    def __init__(self) -> None:
        self._settings = TelegramSettings()
        self._load()

    def _load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE) as f:
                    data = json.load(f)
                self._settings = TelegramSettings(**{**asdict(TelegramSettings()), **data})
                logger.info("Loaded Telegram settings from file")
            except Exception as e:
                logger.error("Failed to load settings: %s", e)

    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(asdict(self._settings), f, indent=2)

    def get(self) -> TelegramSettings:
        return self._settings

    def update(self, **updates: Any) -> TelegramSettings:
        current = asdict(self._settings)
        current.update(updates)
        self._settings = TelegramSettings(**current)
        self._save()
        return self._settings


# --- Singleton getters ---

_template_store: TemplateStore | None = None
_settings_store: SettingsStore | None = None


def get_template_store() -> TemplateStore:
    global _template_store
    if _template_store is None:
        _template_store = TemplateStore()
    return _template_store


def get_settings_store() -> SettingsStore:
    global _settings_store
    if _settings_store is None:
        _settings_store = SettingsStore()
    return _settings_store


# --- Rendering ---


def render_template(template_str: str, variables: dict[str, Any]) -> str:
    """Render a template string with {variable} substitution.

    Unknown variables render as empty string.
    """
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        value = variables.get(var_name, "")
        if value is None:
            return ""
        return str(value)

    result = re.sub(r"\{(\w+)\}", replacer, template_str)

    # Clean up empty lines from unresolved variables
    # but keep intentional single blank lines (from \n\n joins)
    lines = result.split("\n")
    cleaned = []
    for line in lines:
        if line.strip() or (cleaned and cleaned[-1].strip()):
            cleaned.append(line)
    result = "\n".join(cleaned)

    # Collapse multiple blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()
