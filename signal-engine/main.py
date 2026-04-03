"""
Signal Engine — FastAPI Entry Point
====================================
Runs on port 8081. Serves trade signals, backtest, tracker, and config APIs.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.signals import router as signals_router, set_tracker
from api.backtest import router as backtest_router
from api.tracker import router as tracker_router, set_storage
from api.config import router as config_router
from api.market_pulse import router as market_pulse_router
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

# Background task handle
_tracker_task: asyncio.Task | None = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    logger.info("Signal engine starting on %s:%s", config.host, config.port)
    logger.info("Instruments: %s", [i.symbol for i in config.instruments])

    # Wire shared instances
    set_storage(_storage)
    set_tracker(_tracker)

    # Start background tracker check (every 5 minutes)
    global _tracker_task
    _tracker_task = asyncio.create_task(_periodic_tracker_check(300))
    logger.info("Tracker background task started (interval: 300s)")

    yield

    # Cleanup
    if _tracker_task:
        _tracker_task.cancel()
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


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "signal-engine", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
