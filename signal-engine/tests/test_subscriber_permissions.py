"""
Tests for Telegram Bot: Owner vs Subscriber Permissions
========================================================
Tests the command routing, public/owner access control,
subscriber management, and broadcast functionality.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add signal-engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# --- Mock helpers ---

OWNER_CHAT_ID = 123456789
SUBSCRIBER_CHAT_ID = 987654321
GROUP_CHAT_ID = -5002239340

OWNER_SETTINGS_CHATS = [
    {"id": str(OWNER_CHAT_ID), "label": "Owner", "enabled": True}
]


def make_message(chat_id: int, chat_type: str = "private", first_name: str = "Test", text: str = ""):
    return {
        "message_id": 1,
        "from": {"id": chat_id, "first_name": first_name, "is_bot": False},
        "chat": {"id": chat_id, "type": chat_type, "title": "Test Group" if chat_type != "private" else ""},
        "text": text,
    }


def make_notifier():
    """Create a mock notifier that captures sent messages."""
    notifier = MagicMock()
    notifier._send_to_chat = AsyncMock()
    notifier.base_url = "https://api.telegram.org/botTEST"
    return notifier


def make_settings_store(chats=None):
    """Create a mock settings store."""
    settings_data = MagicMock()
    settings_data.chats = chats or OWNER_SETTINGS_CHATS
    store = MagicMock()
    store.get.return_value = settings_data
    return store


def make_subscriber_store(subscribers=None):
    """Create a mock subscriber store."""
    store = MagicMock()
    store.get_all_active.return_value = subscribers or []
    store.get_all.return_value = subscribers or []
    store.get_count.return_value = len(subscribers) if subscribers else 0
    store.is_subscribed.return_value = False
    store.add.return_value = MagicMock(chat_id=str(SUBSCRIBER_CHAT_ID), active=True)
    store.remove.return_value = True
    return store


# --- Tests: Command routing ---


@pytest.mark.asyncio
async def test_owner_can_run_owner_commands():
    """Owner should be able to run restricted commands (no 'restricted' message)."""
    from notifier.commands import _handle_command

    notifier = make_notifier()
    settings_store = make_settings_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store):
        await _handle_command("/pause", OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        notifier._send_to_chat.assert_called_once()
        msg = notifier._send_to_chat.call_args[0][1]
        # Owner should get "paused" confirmation, NOT "restricted"
        assert "restricted" not in msg.lower()
        assert "paused" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_cannot_run_owner_commands():
    """Non-owner subscriber should be blocked from owner commands."""
    from notifier.commands import _handle_command

    notifier = make_notifier()
    settings_store = make_settings_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store):
        await _handle_command("/pause", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        notifier._send_to_chat.assert_called_once()
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_can_run_public_commands():
    """Any user should be able to run public commands (no restriction)."""
    from notifier.commands import _handle_command

    notifier = make_notifier()
    settings_store = make_settings_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store), \
         patch("api.signals._cached_signals", []):
        await _handle_command("/signals", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        notifier._send_to_chat.assert_called_once()
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" not in msg.lower()


@pytest.mark.asyncio
async def test_owner_can_run_public_commands():
    """Owner should also have access to public commands."""
    from notifier.commands import _handle_command

    notifier = make_notifier()
    settings_store = make_settings_store()
    sub_store = make_subscriber_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store), \
         patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _handle_command("/help", OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        notifier._send_to_chat.assert_called_once()
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" not in msg.lower()


@pytest.mark.asyncio
async def test_unknown_command_returns_message():
    """Unknown commands should return a helpful message."""
    from notifier.commands import _handle_command

    notifier = make_notifier()
    settings_store = make_settings_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store):
        await _handle_command("/foobar", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        notifier._send_to_chat.assert_called_once()
        msg = notifier._send_to_chat.call_args[0][1]
        assert "unknown" in msg.lower() or "help" in msg.lower()


# --- Tests: Owner-only commands blocked for subscribers ---


@pytest.mark.asyncio
async def test_subscriber_blocked_from_settings():
    from notifier.commands import _handle_command
    notifier = make_notifier()
    with patch("notifier.commands.get_settings_store", return_value=make_settings_store()):
        await _handle_command("/settings", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_blocked_from_history():
    from notifier.commands import _handle_command
    notifier = make_notifier()
    with patch("notifier.commands.get_settings_store", return_value=make_settings_store()):
        await _handle_command("/history", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_blocked_from_subscribers_list():
    from notifier.commands import _handle_command
    notifier = make_notifier()
    with patch("notifier.commands.get_settings_store", return_value=make_settings_store()):
        await _handle_command("/subscribers", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_blocked_from_broadcast():
    from notifier.commands import _handle_command
    notifier = make_notifier()
    with patch("notifier.commands.get_settings_store", return_value=make_settings_store()):
        await _handle_command("/broadcast hello", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


@pytest.mark.asyncio
async def test_subscriber_blocked_from_resume():
    from notifier.commands import _handle_command
    notifier = make_notifier()
    with patch("notifier.commands.get_settings_store", return_value=make_settings_store()):
        await _handle_command("/resume", SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)
        msg = notifier._send_to_chat.call_args[0][1]
        assert "restricted" in msg.lower()


# --- Tests: Subscribe / Unsubscribe ---
# Handlers use lazy imports: `from .subscribers import get_subscriber_store`
# Must patch at source module: notifier.subscribers


@pytest.mark.asyncio
async def test_start_subscribes_user():
    """/start should auto-subscribe and send welcome."""
    from notifier.commands import _cmd_start

    notifier = make_notifier()
    sub_store = make_subscriber_store()

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        msg = make_message(SUBSCRIBER_CHAT_ID, "private", first_name="Alice")
        await _cmd_start([], SUBSCRIBER_CHAT_ID, msg, notifier)

        sub_store.add.assert_called_once_with(str(SUBSCRIBER_CHAT_ID), "private", "Alice")
        notifier._send_to_chat.assert_called_once()
        welcome = notifier._send_to_chat.call_args[0][1]
        assert "welcome" in welcome.lower() or "subscribed" in welcome.lower()


@pytest.mark.asyncio
async def test_subscribe_new_user():
    """New subscriber gets confirmation."""
    from notifier.commands import _cmd_subscribe

    notifier = make_notifier()
    sub_store = make_subscriber_store()
    sub_store.is_subscribed.return_value = False

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        msg = make_message(SUBSCRIBER_CHAT_ID, "private", first_name="Bob")
        await _cmd_subscribe([], SUBSCRIBER_CHAT_ID, msg, notifier)

        notifier._send_to_chat.assert_called_once()
        reply = notifier._send_to_chat.call_args[0][1]
        assert "subscribed" in reply.lower()


@pytest.mark.asyncio
async def test_subscribe_already_subscribed():
    """Already-subscribed user gets 'already subscribed' message."""
    from notifier.commands import _cmd_subscribe

    notifier = make_notifier()
    sub_store = make_subscriber_store()
    sub_store.is_subscribed.return_value = True

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        msg = make_message(SUBSCRIBER_CHAT_ID, "private", first_name="Bob")
        await _cmd_subscribe([], SUBSCRIBER_CHAT_ID, msg, notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        assert "already" in reply.lower()


@pytest.mark.asyncio
async def test_unsubscribe_active_subscriber():
    """Active subscriber can unsubscribe."""
    from notifier.commands import _cmd_unsubscribe

    notifier = make_notifier()
    sub_store = make_subscriber_store()
    sub_store.remove.return_value = True

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_unsubscribe([], SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        sub_store.remove.assert_called_once_with(str(SUBSCRIBER_CHAT_ID))
        reply = notifier._send_to_chat.call_args[0][1]
        assert "unsubscribed" in reply.lower()


@pytest.mark.asyncio
async def test_unsubscribe_not_subscribed():
    """Non-subscriber trying to unsubscribe gets informed."""
    from notifier.commands import _cmd_unsubscribe

    notifier = make_notifier()
    sub_store = make_subscriber_store()
    sub_store.remove.return_value = False

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_unsubscribe([], SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        assert "not subscribed" in reply.lower()


@pytest.mark.asyncio
async def test_start_group_subscribes_group():
    """/start in a group should subscribe with group title as label."""
    from notifier.commands import _cmd_start

    notifier = make_notifier()
    sub_store = make_subscriber_store()
    msg = make_message(GROUP_CHAT_ID, "supergroup", text="/start")
    msg["chat"]["title"] = "Trading Signals Group"

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_start([], GROUP_CHAT_ID, msg, notifier)

        sub_store.add.assert_called_once_with(str(GROUP_CHAT_ID), "supergroup", "Trading Signals Group")


# --- Tests: Help command ---


@pytest.mark.asyncio
async def test_help_owner_sees_all_commands():
    """Owner help should include owner commands + subscriber count."""
    from notifier.commands import _cmd_help

    notifier = make_notifier()
    settings_store = make_settings_store()
    sub_store = make_subscriber_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store), \
         patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_help([], OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        # Owner commands should appear
        assert "/pause" in reply
        assert "/broadcast" in reply
        assert "/subscribers" in reply
        # Subscriber count should appear (owner only)
        assert "subscriber(s) active" in reply


@pytest.mark.asyncio
async def test_help_subscriber_no_owner_commands():
    """Subscriber help should NOT include owner commands or subscriber count."""
    from notifier.commands import _cmd_help

    notifier = make_notifier()
    settings_store = make_settings_store()
    sub_store = make_subscriber_store()

    with patch("notifier.commands.get_settings_store", return_value=settings_store), \
         patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_help([], SUBSCRIBER_CHAT_ID, make_message(SUBSCRIBER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        # Public commands should appear
        assert "/subscribe" in reply
        assert "/signals" in reply
        # Owner commands should NOT appear
        assert "/pause" not in reply
        assert "/broadcast" not in reply
        assert "/subscribers" not in reply
        # Subscriber count should NOT appear
        assert "subscriber(s) active" not in reply


# --- Tests: Broadcast ---


@pytest.mark.asyncio
async def test_broadcast_no_args():
    """Broadcast with no args should show usage."""
    from notifier.commands import _cmd_broadcast

    notifier = make_notifier()
    sub_store = make_subscriber_store()

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_broadcast([], OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        assert "usage" in reply.lower()


@pytest.mark.asyncio
async def test_broadcast_sends_to_subscribers():
    """Broadcast should send to all active subscribers."""
    from notifier.commands import _cmd_broadcast

    notifier = make_notifier()
    mock_sub1 = MagicMock(chat_id="111", label="User1", active=True)
    mock_sub2 = MagicMock(chat_id="222", label="User2", active=True)
    sub_store = make_subscriber_store([mock_sub1, mock_sub2])

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_broadcast(["hello", "world"], OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        # Should send to each subscriber + the confirmation to owner
        assert notifier._send_to_chat.call_count == 3  # 2 subs + 1 confirmation
        # Check broadcast content was sent to subscribers (📢 prefix)
        calls = [str(c[0][1]) for c in notifier._send_to_chat.call_args_list]
        broadcast_msgs = [c for c in calls if c.startswith("📢")]
        assert len(broadcast_msgs) == 2


@pytest.mark.asyncio
async def test_broadcast_no_subscribers():
    """Broadcast with no subscribers should inform owner."""
    from notifier.commands import _cmd_broadcast

    notifier = make_notifier()
    sub_store = make_subscriber_store([])

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_broadcast(["hello"], OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        assert "no active subscribers" in reply.lower()


@pytest.mark.asyncio
async def test_broadcast_zero_cooldown():
    """Broadcast cooldown at 0 should allow immediate sends."""
    from notifier.commands import _BROADCAST_COOLDOWN

    assert _BROADCAST_COOLDOWN == 0, "Broadcast cooldown should be 0"


# --- Tests: Subscribers list (owner) ---


@pytest.mark.asyncio
async def test_subscribers_list_owner():
    """Owner should see full subscriber list."""
    from notifier.commands import _cmd_subscribers

    notifier = make_notifier()
    mock_sub = MagicMock(chat_id="111", chat_type="private", label="Alice", active=True)
    sub_store = make_subscriber_store([mock_sub])
    sub_store.get_all.return_value = [mock_sub]
    sub_store.get_all_active.return_value = [mock_sub]

    with patch("notifier.subscribers.get_subscriber_store", return_value=sub_store):
        await _cmd_subscribers([], OWNER_CHAT_ID, make_message(OWNER_CHAT_ID), notifier)

        reply = notifier._send_to_chat.call_args[0][1]
        assert "Alice" in reply
        assert "1 active" in reply


# --- Tests: Command registry completeness ---


def test_all_public_commands_registered():
    """Verify all expected public commands are in the registry."""
    from notifier.commands import PUBLIC_COMMANDS

    expected = ["/start", "/subscribe", "/unsubscribe", "/signals", "/status", "/brief", "/check", "/help"]
    for cmd in expected:
        assert cmd in PUBLIC_COMMANDS, f"Missing public command: {cmd}"


def test_all_owner_commands_registered():
    """Verify all expected owner commands are in the registry."""
    from notifier.commands import OWNER_COMMANDS

    expected = ["/pause", "/resume", "/settings", "/history", "/subscribers", "/broadcast"]
    for cmd in expected:
        assert cmd in OWNER_COMMANDS, f"Missing owner command: {cmd}"


def test_no_overlap_between_command_registries():
    """Public and owner command registries should not overlap."""
    from notifier.commands import PUBLIC_COMMANDS, OWNER_COMMANDS

    overlap = set(PUBLIC_COMMANDS.keys()) & set(OWNER_COMMANDS.keys())
    assert len(overlap) == 0, f"Commands exist in both registries: {overlap}"
