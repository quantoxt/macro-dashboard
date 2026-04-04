"""
Fill Simulator
===============
Simulates order fills with spread, slippage, and TP/SL hit detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from config import InstrumentConfig, get_config
from strategies.base import Signal

ExitReason = Literal["TAKE_PROFIT", "STOP_LOSS", "MAX_HOLDING", "END_OF_DATA"]


@dataclass(frozen=True)
class SimulatedFill:
    """Result of a simulated trade."""
    instrument: str
    strategy: str
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    exit_reason: ExitReason
    entry_time: str
    exit_time: str
    pnl_pips: float
    pnl_raw: float
    duration_bars: int
    confidence: int


# Default spread per instrument type (in pips)
DEFAULT_SPREADS: dict[str, float] = {
    "forex": 1.5,
    "metals": 3.0,
    "crypto": 0.0,  # crypto uses percentage
}

CRYPTO_SPREAD_PCT = 0.001  # 0.1%


def _apply_spread(signal: Signal, inst: InstrumentConfig) -> float:
    """Apply spread to the entry price."""
    price = signal.entry

    if inst.asset_type == "crypto":
        spread_amount = price * CRYPTO_SPREAD_PCT
    else:
        spread_pips = DEFAULT_SPREADS.get(inst.asset_type, 2.0)
        spread_amount = spread_pips * inst.pip_size

    # BUY: pay more (ask = mid + half spread)
    # SELL: receive less (bid = mid - half spread)
    half_spread = spread_amount / 2.0

    if signal.direction == "BUY":
        return round(price + half_spread, 5)
    else:
        return round(price - half_spread, 5)


def check_exit(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    direction: str,
    bar_high: float,
    bar_low: float,
) -> ExitReason | None:
    """Check if a bar hit TP or SL.

    Checks which level was hit first based on proximity to bar open.
    For BUY: if low hit SL, that's a loss (regardless of high hitting TP).
    For SELL: if high hit SL, that's a loss.

    Returns None if neither was hit.
    """
    if direction == "BUY":
        # SL is below, TP is above
        hit_sl = bar_low <= stop_loss
        hit_tp = bar_high >= take_profit

        if hit_sl and hit_tp:
            # Both hit — check which is closer to entry (more likely hit first)
            sl_distance = entry_price - stop_loss
            tp_distance = take_profit - entry_price
            return "STOP_LOSS" if sl_distance <= tp_distance else "TAKE_PROFIT"
        elif hit_sl:
            return "STOP_LOSS"
        elif hit_tp:
            return "TAKE_PROFIT"

    else:  # SELL
        # SL is above, TP is below
        hit_sl = bar_high >= stop_loss
        hit_tp = bar_low <= take_profit

        if hit_sl and hit_tp:
            sl_distance = stop_loss - entry_price
            tp_distance = entry_price - take_profit
            return "STOP_LOSS" if sl_distance <= tp_distance else "TAKE_PROFIT"
        elif hit_sl:
            return "STOP_LOSS"
        elif hit_tp:
            return "TAKE_PROFIT"

    return None


def simulate_bar_by_bar(
    signal: Signal,
    entry_price: float,
    df: pd.DataFrame,
    start_idx: int,
    max_bars: int = 50,
    pip_size: float = 0.01,
) -> SimulatedFill | None:
    """Walk forward from entry bar, checking each bar for TP/SL hit.

    Args:
        signal: The generated signal.
        entry_price: Entry price after spread.
        df: Full OHLC DataFrame.
        start_idx: Index of the entry bar.
        max_bars: Max holding period.
        pip_size: Pip size for P&L calculation.

    Returns:
        SimulatedFill when exit triggered, or None if no exit found.
    """
    for offset in range(1, max_bars + 1):
        idx = start_idx + offset
        if idx >= len(df):
            # End of data — close at last available price
            last_bar = df.iloc[-1]
            pnl_raw = _calc_pnl_raw(entry_price, last_bar["close"], signal.direction)
            pnl_pips = pnl_raw / pip_size
            return SimulatedFill(
                instrument=signal.instrument,
                strategy=signal.strategy,
                direction=signal.direction,
                entry_price=entry_price,
                exit_price=last_bar["close"],
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                exit_reason="END_OF_DATA",
                entry_time=str(df.iloc[start_idx]["datetime"]),
                exit_time=str(last_bar["datetime"]),
                pnl_pips=round(pnl_pips, 2),
                pnl_raw=round(pnl_raw, 5),
                duration_bars=offset,
                confidence=signal.confidence,
            )

        bar = df.iloc[idx]
        exit_reason = check_exit(
            entry_price, signal.stop_loss, signal.take_profit,
            signal.direction, bar["high"], bar["low"],
        )

        if exit_reason is not None:
            # Determine exit price
            if exit_reason == "TAKE_PROFIT":
                exit_price = signal.take_profit
            else:
                exit_price = signal.stop_loss

            pnl_raw = _calc_pnl_raw(entry_price, exit_price, signal.direction)
            pnl_pips = pnl_raw / pip_size

            return SimulatedFill(
                instrument=signal.instrument,
                strategy=signal.strategy,
                direction=signal.direction,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                exit_reason=exit_reason,
                entry_time=str(df.iloc[start_idx]["datetime"]),
                exit_time=str(bar["datetime"]),
                pnl_pips=round(pnl_pips, 2),
                pnl_raw=round(pnl_raw, 5),
                duration_bars=offset,
                confidence=signal.confidence,
            )

    # Max holding period — force close at current bar
    close_idx = min(start_idx + max_bars, len(df) - 1)
    bar = df.iloc[close_idx]
    pnl_raw = _calc_pnl_raw(entry_price, bar["close"], signal.direction)
    pnl_pips = pnl_raw / pip_size

    return SimulatedFill(
        instrument=signal.instrument,
        strategy=signal.strategy,
        direction=signal.direction,
        entry_price=entry_price,
        exit_price=bar["close"],
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        exit_reason="MAX_HOLDING",
        entry_time=str(df.iloc[start_idx]["datetime"]),
        exit_time=str(bar["datetime"]),
        pnl_pips=round(pnl_pips, 2),
        pnl_raw=round(pnl_raw, 5),
        duration_bars=max_bars,
        confidence=signal.confidence,
    )


def _calc_pnl_raw(entry: float, exit_price: float, direction: str) -> float:
    """Calculate raw P&L in price units."""
    if direction == "BUY":
        return exit_price - entry
    else:
        return entry - exit_price
