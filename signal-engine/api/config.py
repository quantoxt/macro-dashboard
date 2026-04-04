"""
Strategy Config API
====================
GET /config/strategies — current strategy params
PUT /config/strategies/{strategy_name} — update params (hot reload)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config")


# --- Mutable strategy config store ---
# Defaults mirror the frozen dataclass values from config.py
_strategy_overrides: dict[str, dict[str, Any]] = {}


def _get_defaults() -> dict[str, dict[str, Any]]:
    """Return default config for all strategies."""
    return {
        "confluence_breakout": {
            "enabled": True,
            "minConfidence": 60,
            "minConfirmations": 2,
            "minRiskReward": 1.5,
            "atrSlMultiplier": 1.5,
            "atrTpMultiplier": 2.5,
            "rsiBuyRange": [40.0, 70.0],
            "rsiSellRange": [30.0, 60.0],
            "consolidationBoost": 10,
        },
        "mean_reversion": {
            "enabled": True,
            "minConfidence": 60,
            "minConfirmations": 2,
            "minRiskReward": 1.5,
            "rsiBuyThreshold": 35,
            "rsiSellThreshold": 65,
        },
        "momentum_shift": {
            "enabled": True,
            "minConfidence": 55,
            "minConfirmations": 2,
            "minRiskReward": 2.0,
        },
    }


def is_strategy_enabled(strategy_name: str) -> bool:
    """Check if a strategy is enabled (used by signals API)."""
    defaults = _get_defaults()
    overrides = _strategy_overrides.get(strategy_name, {})
    if "enabled" in overrides:
        return overrides["enabled"]
    return defaults.get(strategy_name, {}).get("enabled", True)


def get_strategy_confidence(strategy_name: str) -> int | None:
    """Get overridden min_confidence for a strategy."""
    overrides = _strategy_overrides.get(strategy_name, {})
    if "minConfidence" in overrides:
        return overrides["minConfidence"]
    return None


class StrategyUpdate(BaseModel):
    """Request body for PUT /config/strategies/{strategy_name}."""
    enabled: bool | None = None
    minConfidence: int | None = None
    minConfirmations: int | None = None
    minRiskReward: float | None = None
    atrSlMultiplier: float | None = None
    atrTpMultiplier: float | None = None
    rsiBuyRange: list[float] | None = None
    rsiSellRange: list[float] | None = None
    rsiBuyThreshold: int | None = None
    rsiSellThreshold: int | None = None
    consolidationBoost: int | None = None


@router.get("/strategies")
async def get_strategies() -> dict[str, Any]:
    """Return current strategy params."""
    defaults = _get_defaults()
    result = {}

    for name, default_params in defaults.items():
        merged = dict(default_params)
        if name in _strategy_overrides:
            merged.update(_strategy_overrides[name])
        result[name] = merged

    return {"strategies": result}


@router.put("/strategies/{strategy_name}")
async def update_strategy(strategy_name: str, update: StrategyUpdate) -> dict[str, Any]:
    """Update strategy params. Changes take effect immediately."""
    defaults = _get_defaults()
    if strategy_name not in defaults:
        raise HTTPException(status_code=404, detail=f"Unknown strategy: {strategy_name}")

    # Validate
    if update.minConfidence is not None and not (0 <= update.minConfidence <= 100):
        raise HTTPException(status_code=400, detail="minConfidence must be 0-100")
    if update.minRiskReward is not None and update.minRiskReward <= 0:
        raise HTTPException(status_code=400, detail="minRiskReward must be > 0")
    if update.minConfirmations is not None and update.minConfirmations < 1:
        raise HTTPException(status_code=400, detail="minConfirmations must be >= 1")
    if update.atrSlMultiplier is not None and update.atrSlMultiplier <= 0:
        raise HTTPException(status_code=400, detail="atrSlMultiplier must be > 0")
    if update.atrTpMultiplier is not None and update.atrTpMultiplier <= 0:
        raise HTTPException(status_code=400, detail="atrTpMultiplier must be > 0")

    # Apply overrides
    changes = update.model_dump(exclude_none=True)
    if strategy_name not in _strategy_overrides:
        _strategy_overrides[strategy_name] = {}
    _strategy_overrides[strategy_name].update(changes)

    logger.info("Config updated for %s: %s", strategy_name, changes)

    # Return updated config
    merged = dict(defaults[strategy_name])
    merged.update(_strategy_overrides[strategy_name])
    return {"strategy": strategy_name, "config": merged}


@router.get("/news-cache")
async def news_cache_status() -> dict[str, Any]:
    """Return current news calendar cache status."""
    from indicators.news import get_news_cache_status
    return get_news_cache_status()


@router.post("/news-cache/refresh")
async def news_cache_refresh() -> dict[str, Any]:
    """Force-refresh the news calendar cache."""
    from indicators.news import fetch_economic_calendar
    events = await fetch_economic_calendar(force_refresh=True)
    return {"refreshed": True, "event_count": len(events)}


@router.get("/vix-cache")
async def vix_cache_status() -> dict[str, Any]:
    """Return current VIX cache status."""
    from indicators.vix import get_vix_cache_status
    return get_vix_cache_status()


@router.get("/notifier")
async def notifier_status() -> dict[str, Any]:
    """Return Telegram notifier status."""
    from notifier.telegram import get_notifier
    notifier = get_notifier()
    if notifier is None:
        return {"enabled": False, "reason": "Not configured (missing env vars or disabled in config)"}
    return {
        "enabled": True,
        "configured": notifier.is_configured,
        "chatId": notifier.chat_id[:4] + "***" + notifier.chat_id[-4:],
        "batchWindow": notifier.batch_window,
    }


@router.post("/notifier/test")
async def notifier_test() -> dict[str, Any]:
    """Send a test Telegram message."""
    from notifier.telegram import get_notifier
    notifier = get_notifier()
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not configured")
    success = await notifier.send_test()
    return {"sent": success}
