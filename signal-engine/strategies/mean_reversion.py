"""
Strategy 2: Mean Reversion Pullback
=====================================
Enter in the direction of the macro trend after a pullback.
Rules from v2/overview-v2.md Strategy 2.
"""

from __future__ import annotations

import logging

import pandas as pd

from config import get_config
from indicators.technical import atr, bollinger_bands, ema, rsi
from indicators.candlestick import detect_rejection_wick
from strategies.base import BaseStrategy, Signal
from strategies.consolidation_detector import detect_consolidation

logger = logging.getLogger(__name__)


class MeanReversion(BaseStrategy):
    """Strategy 2: Mean Reversion Pullback.

    Conditions:
    1. RSI below 35 (BUY pullback) or above 65 (SELL pullback)
    2. Bollinger Band touch — price at/piercing lower band (BUY) or upper (SELL)
    3. H1 rejection candle — long lower wick (BUY) or upper wick (SELL)
    4. H4 TF alignment — pullback must be in the direction of the larger trend

    Base confidence: 40
    """

    name = "mean_reversion"
    min_confidence = 60
    min_confirmations = 2
    min_risk_reward = 1.5

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
        close_h1 = h1_df["close"]

        # --- Indicators ---
        rsi_val = rsi(close_h1, 14).iloc[-1]
        if pd.isna(rsi_val):
            return None

        upper_bb, middle_bb, lower_bb = bollinger_bands(close_h1, 20, 2.0)
        upper_val = upper_bb.iloc[-1]
        lower_val = lower_bb.iloc[-1]
        if pd.isna(upper_val) or pd.isna(lower_val):
            return None

        rejection_strength = detect_rejection_wick(h1_df, min_ratio=0.55)

        # --- Determine direction ---
        # BUY pullback: RSI < 35, price at/below lower BB
        buy_pullback = rsi_val < 35 and current_price <= lower_val * 1.005
        # SELL pullback: RSI > 65, price at/above upper BB
        sell_pullback = rsi_val > 65 and current_price >= upper_val * 0.995

        if not buy_pullback and not sell_pullback:
            return None

        direction = "BUY" if buy_pullback else "SELL"

        # --- Consolidation check ---
        config = get_config()
        inst = config.get_instrument(instrument)
        consolidation = detect_consolidation(h1_df, lookback=20, pip_size=inst.pip_size)

        # During tight consolidation, allow mean reversion (sell resistance, buy support)
        if consolidation.is_consolidating and consolidation.range_type == "tight":
            # Check if price is at the right edge of the range
            if direction == "BUY" and current_price > consolidation.range_low + (consolidation.range_high - consolidation.range_low) * 0.3:
                return None
            if direction == "SELL" and current_price < consolidation.range_high - (consolidation.range_high - consolidation.range_low) * 0.3:
                return None

        # --- Confluence confirmations ---
        confirmations = {}
        reasons = []

        # 1. RSI in pullback zone
        if buy_pullback:
            confirmations["RSI pullback (< 35)"] = True
            reasons.append(f"RSI at {rsi_val:.1f} — oversold pullback")
        elif sell_pullback:
            confirmations["RSI pullback (> 65)"] = True
            reasons.append(f"RSI at {rsi_val:.1f} — overbought pullback")

        # 2. Bollinger Band touch
        if direction == "BUY" and current_price <= lower_val * 1.005:
            confirmations["Bollinger Band touch"] = True
            reasons.append("Price at lower Bollinger Band")
        elif direction == "SELL" and current_price >= upper_val * 0.995:
            confirmations["Bollinger Band touch"] = True
            reasons.append("Price at upper Bollinger Band")

        # 3. Rejection wick
        if rejection_strength > 0.0:
            confirmations["H1 rejection wick"] = True
            reasons.append("H1 rejection wick detected")
        else:
            confirmations["H1 rejection wick"] = False

        # 4. H4 trend alignment
        aligned, penalty = self.check_tf_alignment(h4_df, h1_df, direction)
        if aligned:
            confirmations["H4 trend aligned"] = True
            reasons.append(f"H4 trend: {'BULLISH' if direction == 'BUY' else 'BEARISH'}")
        else:
            confirmations["H4 trend aligned"] = False
            reasons.append("H4 trend misaligned (penalty)")

        # 5. Zone filter
        zone_ok, zone_name = self.check_zone_filter(h1_df, direction)
        if zone_ok:
            confirmations[f"Zone filter ({zone_name})"] = True
            reasons.append(f"Zone: {zone_name}")
        else:
            # Mean reversion allows CAUTIOUS zone
            if zone_name == "CAUTIOUS":
                confirmations["Zone (cautious)"] = True
                reasons.append("Zone: CAUTIOUS (pullback allowed)")
            else:
                confirmations[f"Zone filter ({zone_name})"] = False

        # --- Confidence scoring ---
        base_confidence = 40

        # Bonuses from overview-v2.md
        if confirmations.get("Bollinger Band touch") and confirmations.get("H1 rejection wick"):
            base_confidence += 10  # BB + rejection wick combo

        if confirmations.get("H4 trend aligned"):
            base_confidence += 5

        # Apply penalties
        base_confidence -= int(penalty)

        # Consolidation range trading bonus
        if consolidation.is_consolidating and consolidation.range_type == "tight":
            base_confidence += 5
            reasons.append("Range trading mode (tight consolidation)")

        # Calculate confluence-adjusted confidence
        confidence, _ = self.calculate_confluence_score(confirmations, base_confidence)

        if confidence < self.min_confidence:
            return None

        # Entry at close of rejection candle
        entry = current_price

        return self.generate_signal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            entry=entry,
            h1_df=h1_df,
            reasons=reasons,
            pip_size=pip_size,
        )
