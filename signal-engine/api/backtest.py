"""
Backtest API
=============
POST /backtest — run a backtest with given parameters
GET  /backtest/status — check if a backtest is currently running
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backtest.engine import BacktestConfig, BacktestEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest")

# Track running state
_running = False


class BacktestRequest(BaseModel):
    """Request body for POST /backtest."""
    instruments: list[str] = ["XAUUSD", "XAGUSD", "USDJPY", "GBPJPY", "BTCUSD"]
    strategies: list[str] = ["confluence_breakout", "mean_reversion", "momentum_shift"]
    start_date: str = ""
    end_date: str = ""
    timeframe: str = "1h"
    max_holding_bars: int = 50
    initial_capital: float = 10_000.0


@router.get("/status")
async def backtest_status() -> dict:
    """Check if a backtest is currently running."""
    return {"running": _running}


@router.post("")
async def run_backtest(req: BacktestRequest) -> dict[str, Any]:
    """Run a backtest with the given parameters.

    This is synchronous — large backtests may take time.
    """
    global _running

    if _running:
        return {"error": "A backtest is already running. Please wait."}

    _running = True
    try:
        config = BacktestConfig(
            instruments=req.instruments,
            strategies=req.strategies,
            start_date=req.start_date,
            end_date=req.end_date,
            timeframe=req.timeframe,
            max_holding_bars=req.max_holding_bars,
            initial_capital=req.initial_capital,
        )

        engine = BacktestEngine(config)
        result = engine.run()

        # Serialize fills
        trades = []
        for f in result.fills:
            trades.append({
                "instrument": f.instrument,
                "strategy": f.strategy,
                "direction": f.direction,
                "entry_price": f.entry_price,
                "exit_price": f.exit_price,
                "stop_loss": f.stop_loss,
                "take_profit": f.take_profit,
                "exit_reason": f.exit_reason,
                "pnl_pips": f.pnl_pips,
                "pnl_raw": f.pnl_raw,
                "duration_bars": f.duration_bars,
                "confidence": f.confidence,
                "entry_time": f.entry_time,
                "exit_time": f.exit_time,
            })

        return {
            "config": {
                "instruments": config.instruments,
                "strategies": config.strategies,
                "start_date": config.start_date,
                "end_date": config.end_date,
                "timeframe": config.timeframe,
            },
            "metrics": result.metrics,
            "report": result.report,
            "equityCurve": result.equity_curve,
            "trades": trades,
        }

    except Exception as exc:
        logger.error("Backtest failed: %s", exc, exc_info=True)
        return {"error": str(exc)}

    finally:
        _running = False
