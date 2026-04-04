"""
Signal Engine Configuration
============================
Frozen dataclass config with instruments, timeframes, strategy parameters.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class InstrumentConfig:
    """Single instrument with its Yahoo Finance ticker and pip size."""
    symbol: str
    yahoo_ticker: str
    pip_size: float
    asset_type: str  # "forex", "metals", "crypto"
    max_signals_per_day: int = 3


@dataclass(frozen=True)
class StrategyParams:
    """Parameters for the Confluence Breakout strategy."""
    rsi_buy_range: Tuple[float, float] = (40.0, 70.0)
    rsi_sell_range: Tuple[float, float] = (30.0, 60.0)
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 2.5
    min_risk_reward: float = 1.5
    atr_lookback: int = 20
    min_confirmations: int = 2
    min_confidence: int = 60
    consolidation_boost: int = 10
    # Z-Score settings
    zscore_period: int = 20
    zscore_entry_threshold: float = 2.0
    zscore_enabled: bool = True
    # Volume absorption settings
    volume_absorption_enabled: bool = True
    volume_absorption_threshold: float = 2.0
    volume_absorption_bars: int = 3
    # Consecutive bar confirmation
    consecutive_bar_count: int = 2
    consecutive_bar_enabled: bool = True
    # Trend hierarchy
    trend_hierarchy_enabled: bool = True


@dataclass(frozen=True)
class EngineConfig:
    """Top-level signal engine configuration."""
    host: str = "0.0.0.0"
    port: int = 8081

    # Data settings
    h1_lookback_days: int = 40
    h4_lookback_days: int = 100
    cache_ttl_h1: int = 300    # 5 minutes
    cache_ttl_h4: int = 1800   # 30 minutes
    request_delay_ms: int = 300

    # News calendar settings
    news_calendar_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    news_pause_minutes: int = 15  # pause window before/after high-impact events
    news_cache_ttl: int = 43200   # 12 hours — calendar updates weekly

    # Signal dedup
    signal_cooldown_hours: float = 10.0  # don't re-signal same instrument+strategy after resolution

    # Auto-refresh
    auto_refresh_interval: int = 300  # 5 minutes between background signal refreshes

    # VIX settings
    vix_enabled: bool = True
    vix_sma_period: int = 20
    vix_cache_ttl: int = 3600  # 1 hour

    # Telegram notifier settings
    notifier_enabled: bool = True
    notifier_batch_window: int = 30  # seconds to batch signals
    notifier_outcome_alerts: bool = True  # send WIN/LOSS/EXPIRED notifications

    # Correlation merge (Phase 5)
    correlation_merge_enabled: bool = True
    correlation_confidence_bonus: int = 10  # per additional agreeing strategy

    # Signal frequency limits (Phase 5)
    signal_frequency_limits_enabled: bool = True

    # Instruments
    instruments: Tuple[InstrumentConfig, ...] = (
        InstrumentConfig("XAUUSD", "GC=F",      0.01,  "metals",  max_signals_per_day=3),
        InstrumentConfig("XAGUSD", "SI=F",      0.001, "metals",  max_signals_per_day=3),
        InstrumentConfig("USDJPY", "USDJPY=X",  0.01,  "forex",   max_signals_per_day=5),
        InstrumentConfig("GBPJPY", "GBPJPY=X",  0.01,  "forex",   max_signals_per_day=5),
        InstrumentConfig("BTCUSD", "BTC-USD",   1.0,   "crypto",  max_signals_per_day=5),
    )

    strategy: StrategyParams = StrategyParams()

    def get_instrument(self, symbol: str) -> InstrumentConfig:
        for inst in self.instruments:
            if inst.symbol == symbol:
                return inst
        raise ValueError(f"Unknown instrument: {symbol}")

    def yahoo_ticker_map(self) -> Dict[str, str]:
        return {inst.symbol: inst.yahoo_ticker for inst in self.instruments}


# Singleton
_config: EngineConfig | None = None


def get_config() -> EngineConfig:
    global _config
    if _config is None:
        _config = EngineConfig()
    return _config
