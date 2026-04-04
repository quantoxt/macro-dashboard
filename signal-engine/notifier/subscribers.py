"""
Subscriber System
==================
Manages Telegram bot subscribers who opt in to receive signal notifications.
Separate from the owner's configured chats — subscribers are public opt-in.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
SUBSCRIBERS_FILE = DATA_DIR / "telegram-subscribers.json"


@dataclass
class Subscriber:
    chat_id: str              # Telegram chat ID (string to handle negative group IDs)
    chat_type: str            # "private" | "group" | "supergroup"
    label: str                # Display name (user's first_name for DMs, group title for groups)
    subscribed_at: str        # ISO timestamp
    active: bool = True       # Can be deactivated without removing


class SubscriberStore:
    """Manages subscribers with JSON persistence."""

    def __init__(self):
        self._subscribers: list[Subscriber] = []
        self._load()

    def _load(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SUBSCRIBERS_FILE.exists():
            try:
                with open(SUBSCRIBERS_FILE, "r") as f:
                    data = json.load(f)
                self._subscribers = [Subscriber(**s) for s in data]
                logger.info("Loaded %d subscribers", len(self._subscribers))
            except Exception as e:
                logger.error("Failed to load subscribers: %s", e)
                self._subscribers = []

    def _save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump([asdict(s) for s in self._subscribers], f, indent=2)

    def add(self, chat_id: str, chat_type: str, label: str) -> Subscriber:
        """Add or reactivate a subscriber."""
        for s in self._subscribers:
            if str(s.chat_id) == str(chat_id):
                if not s.active:
                    s.active = True
                    s.subscribed_at = datetime.now(timezone.utc).isoformat()
                    self._save()
                    logger.info("Reactivated subscriber: %s (%s)", label, chat_id)
                return s

        subscriber = Subscriber(
            chat_id=str(chat_id),
            chat_type=chat_type,
            label=label,
            subscribed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._subscribers.append(subscriber)
        self._save()
        logger.info("New subscriber: %s (%s)", label, chat_id)
        return subscriber

    def remove(self, chat_id: str) -> bool:
        """Deactivate a subscriber (soft remove — keeps history)."""
        for s in self._subscribers:
            if str(s.chat_id) == str(chat_id):
                s.active = False
                self._save()
                logger.info("Unsubscribed: %s (%s)", s.label, chat_id)
                return True
        return False

    def is_subscribed(self, chat_id: str) -> bool:
        """Check if a chat ID is an active subscriber."""
        return any(
            str(s.chat_id) == str(chat_id) and s.active
            for s in self._subscribers
        )

    def get_all_active(self) -> list[Subscriber]:
        """Return all active subscribers."""
        return [s for s in self._subscribers if s.active]

    def get_count(self) -> int:
        """Return count of active subscribers."""
        return len(self.get_all_active())

    def get_all(self) -> list[Subscriber]:
        """Return all subscribers (including inactive). Owner-only."""
        return list(self._subscribers)

    def hard_remove(self, chat_id: str) -> bool:
        """Permanently remove a subscriber from storage."""
        original_len = len(self._subscribers)
        self._subscribers = [s for s in self._subscribers if str(s.chat_id) != str(chat_id)]
        if len(self._subscribers) < original_len:
            self._save()
            return True
        return False


# Module-level singleton
_store: SubscriberStore | None = None


def get_subscriber_store() -> SubscriberStore:
    global _store
    if _store is None:
        _store = SubscriberStore()
    return _store
