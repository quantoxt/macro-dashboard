"""
Backtest Engine
================
Walks through historical data bar-by-bar, runs strategies, simulates fills.
Uses the SAME strategy.evaluate() interface as the live engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import EngineConfig, get_config
from data.fetcher import aggregate_to_4h
from backtest.data_loader import fetch_historical
from backtest.simulator import SimulatedFill, _apply_spread, simulate_bar_by_bar
from strategies.base import BaseStrategy, Signal
from strategies.confluence_breakout import ConfluenceBreakout
from strategies.mean_reversion import MeanReversion
from strategies.momentum_shift import MomentumShift

logger = logging.getLogger(__name__)

STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "confluence_breakout": ConfluenceBreakout,
    "mean_reversion": MeanReversion,
    "momentum_shift": MomentumShift,
}

MIN_LOOKBACK = 50  # minimum bars before we can evaluate strategies


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a single backtest run."""
    instruments: list[str] = field(default_factory=lambda: ["XAUUSD", "XAGUSD", "USDJPY", "GBPJPY", "BTCUSD"])
    strategies: list[str] = field(default_factory=lambda: ["confluence_breakout", "mean_reversion", "momentum_shift"])
    start_date: str = ""  # ISO format
    end_date: str = ""
    timeframe: str = "1h"
    max_holding_bars: int = 50
    initial_capital: float = 10_000.0

    def get_start(self) -> datetime:
        if self.start_date:
            return datetime.fromisoformat(self.start_date).replace(tzinfo=timezone.utc)
        return datetime(2026, 1, 1, tzinfo=timezone.utc)

    def get_end(self) -> datetime:
        if self.end_date:
            return datetime.fromisoformat(self.end_date).replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc)


@dataclass
class BacktestResult:
    """Complete backtest output."""
    config: BacktestConfig
    fills: list[SimulatedFill]
    metrics: dict[str, Any] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)


class BacktestEngine:
    """Walk-forward backtest engine.

    For each instrument:
    1. Load historical H1 data (+ aggregate to H4)
    2. Slide a window through the data
    3. At each bar, run each strategy's evaluate()
    4. If signal generated, simulate fill
    5. One position per instrument at a time
    6. Track all fills for metrics
    """

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()
        self.engine_config = get_config()

    def run(self) -> BacktestResult:
        """Run the backtest across all configured instruments and strategies."""
        all_fills: list[SimulatedFill] = []

        strategies = self._init_strategies()

        for instrument in self.config.instruments:
            try:
                fills = self._run_instrument(instrument, strategies)
                all_fills.extend(fills)
            except Exception as exc:
                logger.error("Backtest failed for %s: %s", instrument, exc)

        result = BacktestResult(config=self.config, fills=all_fills)

        # Calculate metrics and report
        from backtest.metrics import calculate_metrics
        from backtest.report import generate_report

        result.metrics = calculate_metrics(all_fills, self.config.initial_capital)
        result.report = generate_report(all_fills, result.metrics, self.config)
        result.equity_curve = self._build_equity_curve(all_fills, self.config.initial_capital)

        return result

    def _init_strategies(self) -> list[BaseStrategy]:
        """Instantiate the requested strategies."""
        result = []
        for name in self.config.strategies:
            cls = STRATEGY_MAP.get(name)
            if cls:
                result.append(cls())
            else:
                logger.warning("Unknown strategy: %s", name)
        return result

    def _run_instrument(
        self, instrument: str, strategies: list[BaseStrategy]
    ) -> list[SimulatedFill]:
        """Run backtest for a single instrument."""
        inst = self.engine_config.get_instrument(instrument)
        logger.info("Backtesting %s (%s) ...", instrument, inst.yahoo_ticker)

        # Load H1 data
        start = self.config.get_start()
        end = self.config.get_end()

        # We need extra history before start for indicator lookback
        fetch_start = start - pd.Timedelta(days=30)

        h1 = fetch_historical(
            inst.yahoo_ticker,
            interval=self.config.timeframe,
            start_date=fetch_start.isoformat(),
            end_date=end.isoformat(),
            use_cache=True,
        )

        if h1.empty or len(h1) < MIN_LOOKBACK + 10:
            logger.warning("Insufficient data for %s: %d bars", instrument, len(h1))
            return []

        # Aggregate H4
        h4 = aggregate_to_4h(h1)
        if h4.empty or len(h4) < MIN_LOOKBACK:
            logger.warning("Insufficient H4 data for %s: %d bars", instrument, len(h4))
            return []

        fills: list[SimulatedFill] = []
        position_free_after_idx = -1  # bars before this index have an open position

        # Determine start index (first bar within date range after lookback)
        start_ts = pd.Timestamp(start)
        start_idx = MIN_LOOKBACK
        for i in range(MIN_LOOKBACK, len(h1)):
            if h1["datetime"].iloc[i] >= start_ts:
                start_idx = i
                break

        for i in range(start_idx, len(h1)):
            # Skip if we have an open position for this instrument
            if i <= position_free_after_idx:
                continue

            # Window for indicators
            h1_window = h1.iloc[max(0, i - 100) : i + 1].reset_index(drop=True)

            # H4 data up to current bar
            current_time = h1["datetime"].iloc[i]
            h4_window = h4[h4["datetime"] <= current_time].tail(100).reset_index(drop=True)

            if len(h1_window) < 30 or len(h4_window) < 30:
                continue

            # Run each strategy
            for strategy in strategies:
                try:
                    sig = strategy.evaluate(
                        instrument, h1_window, h4_window, pip_size=inst.pip_size
                    )
                    if sig is None:
                        continue

                    # Apply spread to entry
                    entry_price = _apply_spread(sig, inst)

                    # Simulate the fill
                    fill = simulate_bar_by_bar(
                        signal=sig,
                        entry_price=entry_price,
                        df=h1,
                        start_idx=i,
                        max_bars=self.config.max_holding_bars,
                        pip_size=inst.pip_size,
                    )

                    if fill is not None:
                        fills.append(fill)
                        # Block new signals until this position closes
                        position_free_after_idx = i + fill.duration_bars

                except Exception as exc:
                    logger.debug("Strategy %s error at bar %d: %s", strategy.name, i, exc)

        return fills

    def _build_equity_curve(
        self, fills: list[SimulatedFill], initial_capital: float
    ) -> list[dict[str, Any]]:
        """Build equity curve from fills sorted by entry time."""
        sorted_fills = sorted(fills, key=lambda f: f.entry_time)
        equity = initial_capital
        curve = [{"date": "start", "equity": round(equity, 2)}]

        for fill in sorted_fills:
            equity += fill.pnl_raw
            curve.append({
                "date": fill.exit_time,
                "equity": round(equity, 2),
            })

        return curve
