"""
Strategy 1: Confluence Breakout
================================
Day-trade signal based on multi-TF alignment + indicator confluence.
Rules from v2/overview-v2.md Strategy 1.
"""

import logging
from typing import Any

import pandas as pd

from config import InstrumentConfig, StrategyParams, get_config
from indicators.technical import atr, average_atr, ema, macd, rsi
from strategies.base import BaseStrategy, Signal
from strategies.consolidation_detector import (
    ConsolidationResult,
    detect_breakout,
    detect_consolidation,
)

logger = logging.getLogger(__name__)


class ConfluenceBreakout(BaseStrategy):
    """Strategy 1: Confluence Breakout for day trading.

    Checks:
    1. Multi-TF alignment (H4 + H1 agree)
    2. RSI between 40-70 (BUY) or 30-60 (SELL)
    3. ATR expanding (> 20-period average)
    4. Price breaks previous H1 candle high/low
    5. MACD histogram increasing in signal direction
    6. Consolidation state (pause during ranges, boost on breakout)
    """

    name = "confluence_breakout"

    def evaluate(
        self,
        instrument: str,
        h1_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        pip_size: float = 0.01,
    ) -> Signal | None:
        """Run the full strategy evaluation.

        Returns a Signal if conditions are met, None otherwise.
        """
        if len(h1_df) < 30 or len(h4_df) < 30:
            logger.debug("%s: not enough data", instrument)
            return None

        # --- Step 1: Determine direction from H1 price action ---
        prev_candle = h1_df.iloc[-2]
        last_candle = h1_df.iloc[-1]
        current_price = last_candle["close"]

        # Break of previous candle high/low
        bullish_break = last_candle["close"] > prev_candle["high"]
        bearish_break = last_candle["close"] < prev_candle["low"]

        if not bullish_break and not bearish_break:
            return None

        direction = "BUY" if bullish_break else "SELL"

        # --- Step 2: Multi-TF alignment ---
        aligned, penalty = self.check_tf_alignment(h4_df, h1_df, direction)

        # --- Step 3: Indicators ---
        close_h1 = h1_df["close"]
        rsi_val = rsi(close_h1, 14).iloc[-1]
        if pd.isna(rsi_val):
            return None

        atr_series = atr(h1_df, 14)
        atr_val = atr_series.iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            return None

        avg_atr_val = average_atr(h1_df, 14, 20).iloc[-1]
        atr_expanding = atr_val > avg_atr_val if not pd.isna(avg_atr_val) else False

        _, _, histogram = macd(close_h1)
        hist_now = histogram.iloc[-1]
        hist_prev = histogram.iloc[-2]
        if pd.isna(hist_now) or pd.isna(hist_prev):
            macd_increasing = False
        elif direction == "BUY":
            macd_increasing = hist_now > hist_prev
        else:
            macd_increasing = hist_now < hist_prev

        # --- Step 4: RSI check ---
        params = self.params
        if direction == "BUY":
            rsi_ok = params.rsi_buy_range[0] <= rsi_val <= params.rsi_buy_range[1]
        else:
            rsi_ok = params.rsi_sell_range[0] <= rsi_val <= params.rsi_sell_range[1]

        # --- Step 5: Consolidation check ---
        config = get_config()
        inst = config.get_instrument(instrument)

        consolidation = detect_consolidation(
            h1_df,
            lookback=20,
            pip_size=inst.pip_size,
        )

        # During consolidation, only signal on breakout
        breakout_dir = None
        if consolidation.is_consolidating:
            breakout_dir = detect_breakout(
                h1_df, consolidation.range_high, consolidation.range_low
            )
            if breakout_dir != direction:
                logger.debug(
                    "%s: consolidating (range %.2f-%.2f), no breakout in %s direction",
                    instrument, consolidation.range_low, consolidation.range_high, direction,
                )
                return None

        # --- Step 6: Build confluence confirmations ---
        confirmations: dict[str, bool] = {}
        reasons: list[str] = []

        # TF alignment
        if aligned:
            confirmations["H4 trend aligned"] = True
            reasons.append(f"H4 trend: {'BULLISH' if direction == 'BUY' else 'BEARISH'}")
        else:
            confirmations["H4 trend aligned"] = False
            reasons.append("H4 trend misaligned (penalty)")

        # RSI
        if rsi_ok:
            confirmations["RSI in range"] = True
            reasons.append(f"RSI at {rsi_val:.1f} — momentum room")
        else:
            confirmations["RSI in range"] = False

        # ATR expanding
        if atr_expanding:
            confirmations["ATR expanding"] = True
            atr_ratio = atr_val / avg_atr_val if avg_atr_val > 0 else 0
            reasons.append(f"ATR expanding ({atr_ratio:.1f}× avg) — breakout fuel")
        else:
            confirmations["ATR expanding"] = False

        # MACD
        if macd_increasing:
            confirmations["MACD histogram increasing"] = True
            reasons.append("MACD histogram increasing")
        else:
            confirmations["MACD histogram increasing"] = False

        # Breakout from consolidation (bonus)
        if consolidation.is_consolidating and breakout_dir == direction:
            confirmations["Breakout from consolidation"] = True
            reasons.append("Breakout from consolidation range")
        elif not consolidation.is_consolidating:
            confirmations["No consolidation detected"] = True
            reasons.append("No consolidation detected")

        # Z-Score confluence
        zs_ok, zs_reason = self.check_zscore_confluence(h1_df, direction)
        if zs_ok:
            confirmations["Z-Score confirms"] = True
            reasons.append(zs_reason)

        # Volume absorption confluence
        absorbed, abs_reason = self.check_volume_absorption(h1_df, direction)
        if absorbed:
            confirmations["Volume absorption"] = True
            reasons.append(abs_reason)

        # --- Step 7: Confidence scoring ---
        base_confidence = 50

        # Apply penalties
        base_confidence -= int(penalty)

        # Bonuses from overview-v2.md
        if aligned:
            base_confidence += 5
        if rsi_ok:
            base_confidence += 5
        if atr_expanding:
            base_confidence += 5
        if macd_increasing:
            base_confidence += 5
        if consolidation.is_consolidating and breakout_dir == direction:
            base_confidence += params.consolidation_boost
        if confirmations.get("Z-Score confirms"):
            base_confidence += 5
        if confirmations.get("Volume absorption"):
            base_confidence += 10

        # Trend hierarchy confluence
        _, trend_reason, trend_adj = self.check_trend_hierarchy(h1_df, direction)
        if trend_reason:
            reasons.append(trend_reason)
        base_confidence += trend_adj

        # Consecutive ATR expansion (breakout momentum)
        if params.consecutive_bar_enabled:
            from indicators.technical import consecutive_extreme
            atr_diff = atr(h1_df, 14).diff()
            if consecutive_extreme(atr_diff, 0, "above", bars=params.consecutive_bar_count):
                base_confidence += 5
                reasons.append(f"ATR expanding {params.consecutive_bar_count} bars")

        # Calculate confluence-adjusted confidence
        confidence, confluence_reasons = self.calculate_confluence_score(
            confirmations, base_confidence
        )

        # Merge reason lists
        final_reasons = reasons + [
            f"Confluence: {sum(1 for v in confirmations.values() if v)} confirmations"
        ]

        if confidence < self.min_confidence:
            logger.debug(
                "%s: %s signal rejected — confidence %d",
                instrument, direction, confidence,
            )
            return None

        return self.generate_signal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            entry=current_price,
            h1_df=h1_df,
            reasons=final_reasons,
        )
