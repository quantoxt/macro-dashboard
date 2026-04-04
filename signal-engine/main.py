"""
Signal Engine — FastAPI Entry Point
====================================
Runs on port 8081. Serves trade signals, backtest, tracker, and config APIs.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env from signal-engine directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.signals import router as signals_router, set_tracker, set_storage, auto_refresh_signals
from api.backtest import router as backtest_router
from api.tracker import router as tracker_router, set_storage as set_tracker_storage
from api.config import router as config_router
from api.market_pulse import router as market_pulse_router
from api.telegram import router as telegram_router
from config import get_config
from tracker.storage import SignalStorage
from tracker.tracker import SignalTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Shared instances
_storage = SignalStorage()
_tracker = SignalTracker(_storage)

# Background task handles
_tracker_task: asyncio.Task | None = None
_refresh_task: asyncio.Task | None = None
_command_task: asyncio.Task | None = None


async def _periodic_tracker_check(interval_seconds: int = 300) -> None:
    """Background task: check pending signals every N seconds."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            checked = await _tracker.check_pending_signals()
            if checked > 0:
                logger.info("Tracker check: resolved %d signals", checked)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Tracker background check failed: %s", exc)


async def _periodic_signal_refresh(interval_seconds: int = 300) -> None:
    """Background task: fetch data + run strategies every N seconds."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            count = await auto_refresh_signals()
            if count > 0:
                logger.info("Auto-refresh: generated %d signal(s)", count)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Auto-refresh background task failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    logger.info("Signal engine starting on %s:%s", config.host, config.port)
    logger.info("Instruments: %s", [i.symbol for i in config.instruments])

    # Wire shared instances
    set_storage(_storage)
    set_tracker_storage(_storage)
    set_tracker(_tracker)

    # Start background tracker check (every 5 minutes)
    global _tracker_task, _refresh_task
    _tracker_task = asyncio.create_task(_periodic_tracker_check(300))
    logger.info("Tracker background task started (interval: 300s)")

    # Start background signal refresh
    _refresh_task = asyncio.create_task(
        _periodic_signal_refresh(config.auto_refresh_interval)
    )
    logger.info("Auto-refresh task started (interval: %ds)", config.auto_refresh_interval)

    # Initialize Telegram notifier (if configured)
    global _command_task
    if config.notifier_enabled:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            # Initialize settings + templates
            from notifier.templates import get_template_store, get_settings_store
            get_template_store()
            get_settings_store()

            from notifier.telegram import TelegramNotifier, set_notifier
            notifier = TelegramNotifier(
                bot_token=bot_token,
                chat_id=chat_id,
                batch_window=config.notifier_batch_window,
            )
            set_notifier(notifier)
            logger.info("Telegram notifier initialized (chat_id: %s)", chat_id)

            # Ensure settings primary chat matches env var
            settings_store = get_settings_store()
            cur = settings_store.get()
            primary_id = cur.chats[0].get("id", "") if cur.chats else ""
            if not str(primary_id).strip().lstrip("-").isdigit():
                settings_store.update(chats=[
                    {"id": chat_id, "label": "Primary", "enabled": True}
                ])
            try:
                await notifier.send_test()
            except Exception as exc:
                logger.warning("Telegram test message failed: %s", exc)

            # Start bot command polling
            try:
                from notifier.commands import poll_for_updates, register_bot_commands
                await register_bot_commands(notifier)
                _command_task = asyncio.create_task(poll_for_updates())
                logger.info("Bot command polling started")
            except Exception as exc:
                logger.warning("Bot command setup failed: %s", exc)
        else:
            logger.warning(
                "Telegram notifier enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"
            )
    else:
        logger.info("Telegram notifier disabled by config")

    yield

    # Cleanup
    if _tracker_task:
        _tracker_task.cancel()
    if _refresh_task:
        _refresh_task.cancel()
    if _command_task:
        _command_task.cancel()
    logger.info("Signal engine shutting down")


app = FastAPI(
    title="Macro Dashboard Signal Engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals_router, tags=["signals"])
app.include_router(backtest_router, tags=["backtest"])
app.include_router(tracker_router, tags=["tracker"])
app.include_router(config_router, tags=["config"])
app.include_router(market_pulse_router, tags=["market-pulse"])
app.include_router(telegram_router, tags=["telegram"])


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "signal-engine", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    port = int(os.environ.get("PORT", config.port))
    uvicorn.run(
        "main:app",
        host=config.host,
        port=port,
        reload=False,
    )
