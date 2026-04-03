"""
Strategy Base Class & Signal Data Model
========================================
Confluence scoring, TF alignment, S/R-anchored SL, ATR-based TP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import InstrumentConfig, StrategyParams, get_config
from indicators.technical import atr, ema
from indicators.structure import SRLevel, detect_support_resistance, find_nearest_sr
from indicators.fibonacci import fib_tp_target
from indicators.trendlines import ZoneResult, calculate_trend_lines, check_zone_permission
from indicators.news import NewsPauseResult, check_news_pause, get_current_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Signal:
    """A single trade signal produced by a strategy."""
    instrument: str
    direction: str  # "BUY" | "SELL"
    confidence: int  # 0-100
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    strategy: str
    timeframe: str
    reasons: list[str]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BaseStrategy:
    """Base class for all signal strategies.

    Provides:
    - Minimum confluence check (>= 2 confirmations)
    - H4/H1 timeframe alignment
    - S/R-anchored stop loss merged with ATR minimum
    - ATR-based take profit with minimum R:R
    - Signal validation and construction
    """

    name: str = "base"
    min_confidence: int = 60
    min_confirmations: int = 2
    min_risk_reward: float = 1.5

    def __init__(self, params: StrategyParams | None = None):
        self.params = params or get_config().strategy

    def check_tf_alignment(
        self, h4_df: pd.DataFrame, h1_df: pd.DataFrame, direction: str
    ) -> tuple[bool, float]:
        """Check if H4 trend agrees with H1 direction.

        Returns (aligned: bool, penalty: float).
        penalty > 0 means a confidence reduction.
        """
        if len(h4_df) < 50 or len(h1_df) < 20:
            return False, 20.0

        close_h4 = h4_df["close"]
        ema20_h4 = ema(close_h4, 20)
        ema50_h4 = ema(close_h4, 50)

        h4_bullish = ema20_h4.iloc[-1] > ema50_h4.iloc[-1]
        h4_bearish = ema20_h4.iloc[-1] < ema50_h4.iloc[-1]

        if direction == "BUY" and h4_bullish:
            return True, 0.0
        elif direction == "BUY" and h4_bearish:
            return False, 15.0
        elif direction == "SELL" and h4_bearish:
            return True, 0.0
        elif direction == "SELL" and h4_bullish:
            return False, 15.0

        # Neutral H4 — slight penalty
        return True, 5.0

    def check_zone_filter(
        self, h1_df: pd.DataFrame, direction: str
    ) -> tuple[bool, str]:
        """Check if the signal direction is permitted by the buy/sell zone.

        Returns (permitted: bool, zone_name: str).
        """
        zone = calculate_trend_lines(h1_df)
        permitted = check_zone_permission(direction, zone.zone)
        return permitted, zone.zone

    def calculate_confluence_score(
        self, confirmations: dict[str, bool], base_confidence: int
    ) -> tuple[int, list[str]]:
        """Count confirmations and adjust confidence.

        Each True confirmation adds a confidence bonus.
        Returns (adjusted_confidence, list_of_passed_reasons).
        """
        count = sum(1 for v in confirmations.values() if v)
        reasons = [k for k, v in confirmations.items() if v]

        if count < self.min_confirmations:
            return 0, reasons

        # More confirmations = more confidence
        bonus = (count - self.min_confirmations) * 5
        adjusted = min(100, base_confidence + bonus)

        # 4+ confirmations = "high conviction" badge (extra boost)
        if count >= 4:
            adjusted = min(100, adjusted + 5)

        return adjusted, reasons

    def calculate_sl(
        self,
        entry: float,
        direction: str,
        df: pd.DataFrame,
        sr_levels: list[SRLevel],
    ) -> float:
        """S/R-anchored SL merged with ATR minimum.

        Use whichever is FURTHER from entry.
        """
        atr_val = atr(df, 14).iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            atr_val = entry * 0.005  # 0.5% fallback

        atr_distance = self.params.atr_sl_multiplier * atr_val

        # Find nearest structural S/R in stop direction
        if direction == "BUY":
            sr_level = find_nearest_sr(entry, sr_levels, "below")
        else:
            sr_level = find_nearest_sr(entry, sr_levels, "above")

        if sr_level is not None:
            sr_distance = abs(entry - sr_level.price)
        else:
            sr_distance = 0.0

        # Use whichever is further
        distance = max(atr_distance, sr_distance)

        if direction == "BUY":
            return round(entry - distance, 5)
        else:
            return round(entry + distance, 5)

    def calculate_tp(
        self,
        entry: float,
        stop_loss: float,
        direction: str = "BUY",
        h1_df: pd.DataFrame | None = None,
        sr_levels: list[SRLevel] | None = None,
        pip_size: float = 0.01,
    ) -> tuple[float, bool]:
        """Calculate TP: try Fib first, fall back to ATR.

        Returns (tp_price, used_fib: bool).
        """
        used_fib = False
        tp = None

        # Try Fibonacci-based TP
        if h1_df is not None and sr_levels is not None:
            tp = fib_tp_target(
                entry, direction, h1_df, sr_levels, pip_size=pip_size
            )
            if tp is not None:
                # Verify minimum R:R
                rr = abs(tp - entry) / max(abs(entry - stop_loss), 1e-10)
                if rr >= self.min_risk_reward:
                    used_fib = True
                else:
                    tp = None  # Fib target too close, fall back

        # Fallback: ATR-based TP
        if tp is None:
            atr_distance = abs(entry - stop_loss) / self.params.atr_sl_multiplier
            tp_distance = self.params.atr_tp_multiplier * atr_distance

            if entry > stop_loss:  # BUY
                tp = entry + tp_distance
            else:  # SELL
                tp = entry - tp_distance

            # Enforce minimum R:R
            rr = abs(tp - entry) / abs(entry - stop_loss)
            if rr < self.min_risk_reward:
                if entry > stop_loss:
                    tp = entry + self.min_risk_reward * abs(entry - stop_loss)
                else:
                    tp = entry - self.min_risk_reward * abs(entry - stop_loss)

        return round(tp, 5), used_fib

    def generate_signal(
        self,
        instrument: str,
        direction: str,
        confidence: int,
        entry: float,
        h1_df: pd.DataFrame,
        reasons: list[str],
        pip_size: float = 0.01,
    ) -> Signal | None:
        """Build and validate a Signal. Returns None if invalid."""
        if confidence < self.min_confidence:
            logger.debug(
                "%s: %s signal rejected — confidence %d < %d",
                self.name, instrument, confidence, self.min_confidence,
            )
            return None

        # Zone filter — reject wrong-direction signals
        zone_ok, zone_name = self.check_zone_filter(h1_df, direction)
        if not zone_ok:
            logger.debug(
                "%s: %s %s signal rejected — zone is %s",
                self.name, instrument, direction, zone_name,
            )
            return None

        sr_levels = detect_support_resistance(h1_df)
        sl = self.calculate_sl(entry, direction, h1_df, sr_levels)
        tp, used_fib = self.calculate_tp(
            entry, sl, direction, h1_df, sr_levels, pip_size
        )

        rr = abs(tp - entry) / max(abs(entry - sl), 1e-10)

        if rr < self.min_risk_reward:
            logger.debug(
                "%s: %s signal rejected — R:R %.2f < %.2f",
                self.name, instrument, rr, self.min_risk_reward,
            )
            return None

        # Add Fib TP to reasons if used
        final_reasons = list(reasons)
        if used_fib:
            final_reasons.append("TP at Fib extension level")
        final_reasons.append(f"Zone: {zone_name}")

        return Signal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            entry=round(entry, 5),
            stop_loss=sl,
            take_profit=tp,
            risk_reward=round(rr, 2),
            strategy=self.name,
            timeframe="H1",
            reasons=final_reasons,
        )
