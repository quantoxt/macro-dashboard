"""
Strategy 3: Momentum Shift (Early Signal)
===========================================
Catch the turn before everyone else sees it.
Rules from v2/overview-v2.md Strategy 3.

Note: Weekly delta and MA20 signal flips require yield/heatmap data
which isn't wired yet. Phase 2 adaptation: use H4 EMA crossover
as the "flip" signal instead.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from config import get_config
from indicators.technical import atr, ema, rsi
from strategies.base import BaseStrategy, Signal

logger = logging.getLogger(__name__)


def _current_session() -> str:
    """Return current trading session based on UTC hour."""
    hour = datetime.now(timezone.utc).hour
    if 0 <= hour < 7:
        return "ASIAN"
    elif 7 <= hour < 13:
        return "EUROPEAN"
    else:
        return "US"


def _ema_crossover_flip(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> str | None:
    """Detect recent EMA crossover flip.

    Returns "BUY" if fast crossed above slow, "SELL" if below, None if no recent flip.
    "Recent" = happened within the last 5 candles.
    """
    if len(df) < slow + 5:
        return None

    close = df["close"]
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)

    diff = fast_ema - slow_ema

    # Check if a crossover happened in the last 5 candles
    for i in range(-5, 0):
        if pd.isna(diff.iloc[i]) or pd.isna(diff.iloc[i - 1]):
            continue
        # Positive crossover (fast crosses above slow)
        if diff.iloc[i - 1] <= 0 and diff.iloc[i] > 0:
            return "BUY"
        # Negative crossover (fast crosses below slow)
        if diff.iloc[i - 1] >= 0 and diff.iloc[i] < 0:
            return "SELL"

    return None


class MomentumShift(BaseStrategy):
    """Strategy 3: Momentum Shift (Early Signal).

    Conditions:
    1. H4 EMA crossover flip (proxy for weekly delta + MA20 flip)
    2. RSI crossing 50 line in new direction
    3. Volume increasing (for crypto/metals)
    4. Session awareness — penalty during Asian session for forex

    Base confidence: 35
    """

    name = "momentum_shift"
    min_confidence = 55
    min_confirmations = 2
    min_risk_reward = 2.0  # 2:1 for momentum shifts

    def evaluate(
        self,
        instrument: str,
        h1_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        pip_size: float = 0.01,
    ) -> Signal | None:
        """Run the full strategy evaluation."""
        if len(h1_df) < 30 or len(h4_df) < 30:
            return None

        current_price = h1_df["close"].iloc[-1]

        # --- 1. H4 EMA crossover flip ---
        h4_flip = _ema_crossover_flip(h4_df, fast=9, slow=21)
        if h4_flip is None:
            return None

        direction = h4_flip

        # --- 2. RSI crossing 50 line ---
        close_h1 = h1_df["close"]
        rsi_series = rsi(close_h1, 14)
        rsi_now = rsi_series.iloc[-1]
        rsi_prev = rsi_series.iloc[-2]

        if pd.isna(rsi_now) or pd.isna(rsi_prev):
            return None

        # RSI 50-line cross in signal direction
        rsi_cross_buy = rsi_prev <= 50 and rsi_now > 50
        rsi_cross_sell = rsi_prev >= 50 and rsi_now < 50

        rsi_crossed = (direction == "BUY" and rsi_cross_buy) or \
                      (direction == "SELL" and rsi_cross_sell)

        # Even if not exactly crossed this candle, RSI should be on the right side
        rsi_aligned = (direction == "BUY" and rsi_now > 45) or \
                      (direction == "SELL" and rsi_now < 55)

        if not rsi_aligned:
            return None

        # --- 3. Volume check (for crypto/metals) ---
        inst = get_config().get_instrument(instrument)
        volume_increasing = False
        if inst.asset_type in ("crypto", "metals") and "volume" in h1_df.columns:
            vol_series = h1_df["volume"]
            if len(vol_series) >= 20:
                vol_ma = vol_series.rolling(20).mean().iloc[-1]
                vol_current = vol_series.iloc[-1]
                if not pd.isna(vol_ma) and vol_ma > 0:
                    volume_increasing = vol_current > vol_ma * 1.15

        # --- 4. ATR confirming volatility ---
        atr_series = atr(h1_df, 14)
        atr_now = atr_series.iloc[-1]
        atr_avg = atr_series.rolling(20).mean().iloc[-1]
        atr_confirming = not pd.isna(atr_now) and not pd.isna(atr_avg) and atr_now > atr_avg

        # --- Session ---
        session = _current_session()
        session_penalty = 0
        if session == "ASIAN" and inst.asset_type == "forex":
            session_penalty = 5

        # --- Confluence confirmations ---
        confirmations = {}
        reasons = []

        # EMA crossover flip
        confirmations["H4 EMA crossover flip"] = True
        reasons.append(f"H4 EMA flip → {direction}")

        # RSI 50 cross
        if rsi_crossed:
            confirmations["RSI 50-line cross"] = True
            reasons.append(f"RSI crossed 50 → {direction}")
        else:
            confirmations["RSI 50-line cross"] = False

        # ATR confirming
        if atr_confirming:
            confirmations["ATR expanding"] = True
            reasons.append("ATR expanding — momentum fuel")
        else:
            confirmations["ATR expanding"] = False

        # Volume
        if volume_increasing:
            confirmations["Volume increasing"] = True
            reasons.append("Volume increasing")
        else:
            confirmations["Volume increasing"] = False

        # Zone filter
        zone_ok, zone_name = self.check_zone_filter(h1_df, direction)
        if zone_ok:
            confirmations[f"Zone ({zone_name})"] = True
        else:
            confirmations[f"Zone ({zone_name})"] = False

        # --- Confidence scoring ---
        base_confidence = 35

        # Bonuses from overview-v2.md
        if rsi_crossed:
            base_confidence += 10
        if confirmations.get("ATR expanding"):
            base_confidence += 5
        if confirmations.get("Volume increasing"):
            base_confidence += 5

        # Session penalty
        base_confidence -= session_penalty
        if session_penalty > 0:
            reasons.append(f"Session: {session} (forex penalty)")

        # Calculate confluence-adjusted confidence
        confidence, _ = self.calculate_confluence_score(confirmations, base_confidence)

        if confidence < self.min_confidence:
            return None

        return self.generate_signal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            entry=current_price,
            h1_df=h1_df,
            reasons=reasons,
            pip_size=pip_size,
        )
