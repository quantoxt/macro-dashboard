"""
Performance Metrics
====================
Calculates comprehensive backtest metrics from simulated fills.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backtest.simulator import SimulatedFill


@dataclass
class BacktestMetrics:
    """All performance metrics from a backtest run."""
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    total_pnl_pips: float
    total_pnl_raw: float
    avg_win_pips: float
    avg_loss_pips: float
    avg_win_raw: float
    avg_loss_raw: float
    expectancy_pips: float
    expectancy_raw: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_duration_bars: float
    trades_per_day: float
    recovery_factor: float
    best_trade_pips: float
    worst_trade_pips: float
    consecutive_wins: int
    consecutive_losses: int


def calculate_metrics(
    fills: list[SimulatedFill],
    initial_capital: float = 10_000.0,
) -> dict[str, float | int]:
    """Calculate all metrics from a list of simulated fills.

    Returns a dict suitable for JSON serialization.
    """
    if not fills:
        return _empty_metrics()

    wins = [f for f in fills if f.pnl_pips > 0]
    losses = [f for f in fills if f.pnl_pips <= 0]

    total_trades = len(fills)
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / total_trades if total_trades > 0 else 0.0

    # P&L totals
    total_pnl_pips = sum(f.pnl_pips for f in fills)
    total_pnl_raw = sum(f.pnl_raw for f in fills)

    gross_profit = sum(f.pnl_pips for f in wins)
    gross_loss = abs(sum(f.pnl_pips for f in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Averages
    avg_win_pips = gross_profit / n_wins if n_wins > 0 else 0.0
    avg_loss_pips = gross_loss / n_losses if n_losses > 0 else 0.0
    avg_win_raw = sum(f.pnl_raw for f in wins) / n_wins if n_wins > 0 else 0.0
    avg_loss_raw = abs(sum(f.pnl_raw for f in losses)) / n_losses if n_losses > 0 else 0.0

    # Expectancy
    expectancy_pips = total_pnl_pips / total_trades if total_trades > 0 else 0.0
    expectancy_raw = total_pnl_raw / total_trades if total_trades > 0 else 0.0

    # Duration
    avg_duration = sum(f.duration_bars for f in fills) / total_trades if total_trades > 0 else 0.0

    # Trades per day (rough: count unique trading days)
    unique_days = set()
    for f in fills:
        date_str = f.entry_time[:10] if len(f.entry_time) >= 10 else f.entry_time
        unique_days.add(date_str)
    n_days = max(len(unique_days), 1)
    trades_per_day = total_trades / n_days

    # Best / worst
    best_trade = max((f.pnl_pips for f in fills), default=0.0)
    worst_trade = min((f.pnl_pips for f in fills), default=0.0)

    # Streaks
    consecutive_wins = _max_streak([1 if f.pnl_pips > 0 else 0 for f in fills], 1)
    consecutive_losses = _max_streak([1 if f.pnl_pips > 0 else 0 for f in fills], 0)

    # Equity curve for drawdown
    pnl_series = [f.pnl_raw for f in fills]
    equity = initial_capital
    equity_peaks = [initial_capital]
    for pnl in pnl_series:
        equity += pnl
        equity_peaks.append(equity)

    # Drawdown
    max_dd, max_dd_pct = _calculate_drawdown(equity_peaks)

    # Sharpe (annualized)
    sharpe = _calculate_sharpe(pnl_series)

    # Recovery factor
    recovery_factor = total_pnl_raw / abs(max_dd) if max_dd != 0 else float("inf")

    return {
        "total_trades": total_trades,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
        "total_pnl_pips": round(total_pnl_pips, 2),
        "total_pnl_raw": round(total_pnl_raw, 2),
        "avg_win_pips": round(avg_win_pips, 2),
        "avg_loss_pips": round(avg_loss_pips, 2),
        "avg_win_raw": round(avg_win_raw, 5),
        "avg_loss_raw": round(avg_loss_raw, 5),
        "expectancy_pips": round(expectancy_pips, 2),
        "expectancy_raw": round(expectancy_raw, 5),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 5),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "avg_duration_bars": round(avg_duration, 1),
        "trades_per_day": round(trades_per_day, 2),
        "recovery_factor": round(recovery_factor, 4) if recovery_factor != float("inf") else None,
        "best_trade_pips": round(best_trade, 2),
        "worst_trade_pips": round(worst_trade, 2),
        "consecutive_wins": consecutive_wins,
        "consecutive_losses": consecutive_losses,
    }


def _empty_metrics() -> dict[str, float | int]:
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "profit_factor": None,
        "total_pnl_pips": 0.0,
        "total_pnl_raw": 0.0,
        "avg_win_pips": 0.0,
        "avg_loss_pips": 0.0,
        "avg_win_raw": 0.0,
        "avg_loss_raw": 0.0,
        "expectancy_pips": 0.0,
        "expectancy_raw": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_pct": 0.0,
        "avg_duration_bars": 0.0,
        "trades_per_day": 0.0,
        "recovery_factor": None,
        "best_trade_pips": 0.0,
        "worst_trade_pips": 0.0,
        "consecutive_wins": 0,
        "consecutive_losses": 0,
    }


def _max_streak(indicators: list[int], target: int) -> int:
    """Find the longest consecutive streak of target values."""
    max_s = 0
    current = 0
    for v in indicators:
        if v == target:
            current += 1
            max_s = max(max_s, current)
        else:
            current = 0
    return max_s


def _calculate_drawdown(equity_curve: list[float]) -> tuple[float, float]:
    """Calculate max drawdown (absolute and percentage) from equity curve."""
    if not equity_curve:
        return 0.0, 0.0

    arr = np.array(equity_curve)
    running_max = np.maximum.accumulate(arr)
    drawdowns = arr - running_max
    max_dd = abs(drawdowns.min())

    # Percentage: relative to the peak at that point
    dd_pct = 0.0
    for i in range(len(arr)):
        if running_max[i] > 0:
            pct = abs((arr[i] - running_max[i]) / running_max[i]) * 100
            dd_pct = max(dd_pct, pct)

    return float(max_dd), float(dd_pct)


def _calculate_sharpe(pnl_series: list[float]) -> float:
    """Calculate annualized Sharpe ratio from P&L series."""
    if len(pnl_series) < 2:
        return 0.0

    arr = np.array(pnl_series)
    std = np.std(arr)
    if std == 0:
        return 0.0

    mean = np.mean(arr)
    # Assume ~252 trading days, ~24 hourly bars per day for hourly data
    # Sharpe = (mean / std) * sqrt(bars_per_year)
    # For hourly: ~252 * 6 = ~1512 usable bars/year (conservative)
    sharpe = (mean / std) * np.sqrt(1512)
    return float(sharpe)
