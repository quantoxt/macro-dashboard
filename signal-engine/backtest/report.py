"""
Backtest Report Generator
==========================
Generates per-instrument, per-strategy, and overall summaries.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backtest.simulator import SimulatedFill


def generate_report(
    fills: list[SimulatedFill],
    metrics: dict[str, Any],
    config: Any,
) -> dict[str, Any]:
    """Generate a comprehensive backtest report.

    Returns a dict suitable for JSON serialization.
    """
    if not fills:
        return {
            "summary": {"message": "No trades generated during backtest period"},
            "per_instrument": {},
            "per_strategy": {},
            "monthly_breakdown": {},
            "top_trades": [],
            "bottom_trades": [],
        }

    return {
        "summary": _overall_summary(fills, metrics),
        "per_instrument": _per_instrument(fills),
        "per_strategy": _per_strategy(fills),
        "monthly_breakdown": _monthly_breakdown(fills),
        "top_trades": _top_trades(fills, n=10),
        "bottom_trades": _bottom_trades(fills, n=10),
    }


def _overall_summary(
    fills: list[SimulatedFill], metrics: dict[str, Any]
) -> dict[str, Any]:
    return {
        "total_trades": metrics.get("total_trades", 0),
        "win_rate": metrics.get("win_rate", 0),
        "profit_factor": metrics.get("profit_factor"),
        "sharpe_ratio": metrics.get("sharpe_ratio", 0),
        "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
        "total_pnl_pips": metrics.get("total_pnl_pips", 0),
        "expectancy_pips": metrics.get("expectancy_pips", 0),
        "recovery_factor": metrics.get("recovery_factor"),
    }


def _per_instrument(fills: list[SimulatedFill]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[SimulatedFill]] = defaultdict(list)
    for f in fills:
        grouped[f.instrument].append(f)

    result = {}
    for instrument, ifills in grouped.items():
        wins = [f for f in ifills if f.pnl_pips > 0]
        total = len(ifills)
        result[instrument] = {
            "total_trades": total,
            "wins": len(wins),
            "win_rate": round(len(wins) / total, 4) if total > 0 else 0,
            "total_pnl_pips": round(sum(f.pnl_pips for f in ifills), 2),
            "avg_confidence": round(sum(f.confidence for f in ifills) / total, 1) if total > 0 else 0,
        }
    return result


def _per_strategy(fills: list[SimulatedFill]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[SimulatedFill]] = defaultdict(list)
    for f in fills:
        grouped[f.strategy].append(f)

    result = {}
    for strategy, sfills in grouped.items():
        wins = [f for f in sfills if f.pnl_pips > 0]
        total = len(sfills)
        result[strategy] = {
            "total_trades": total,
            "wins": len(wins),
            "win_rate": round(len(wins) / total, 4) if total > 0 else 0,
            "total_pnl_pips": round(sum(f.pnl_pips for f in sfills), 2),
            "avg_confidence": round(sum(f.confidence for f in sfills) / total, 1) if total > 0 else 0,
        }
    return result


def _monthly_breakdown(fills: list[SimulatedFill]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[SimulatedFill]] = defaultdict(list)
    for f in fills:
        # Extract YYYY-MM from entry_time
        month_key = f.entry_time[:7] if len(f.entry_time) >= 7 else "unknown"
        grouped[month_key].append(f)

    result = {}
    for month, mfills in sorted(grouped.items()):
        wins = [f for f in mfills if f.pnl_pips > 0]
        total = len(mfills)
        result[month] = {
            "trades": total,
            "wins": len(wins),
            "win_rate": round(len(wins) / total, 4) if total > 0 else 0,
            "pnl_pips": round(sum(f.pnl_pips for f in mfills), 2),
        }
    return result


def _top_trades(fills: list[SimulatedFill], n: int = 10) -> list[dict[str, Any]]:
    sorted_fills = sorted(fills, key=lambda f: f.pnl_pips, reverse=True)
    return [_fill_to_dict(f) for f in sorted_fills[:n]]


def _bottom_trades(fills: list[SimulatedFill], n: int = 10) -> list[dict[str, Any]]:
    sorted_fills = sorted(fills, key=lambda f: f.pnl_pips)
    return [_fill_to_dict(f) for f in sorted_fills[:n]]


def _fill_to_dict(f: SimulatedFill) -> dict[str, Any]:
    return {
        "instrument": f.instrument,
        "strategy": f.strategy,
        "direction": f.direction,
        "entry_price": f.entry_price,
        "exit_price": f.exit_price,
        "exit_reason": f.exit_reason,
        "pnl_pips": f.pnl_pips,
        "pnl_raw": f.pnl_raw,
        "duration_bars": f.duration_bars,
        "confidence": f.confidence,
        "entry_time": f.entry_time,
        "exit_time": f.exit_time,
    }
