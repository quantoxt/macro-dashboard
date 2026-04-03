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

    # Instruments
    instruments: Tuple[InstrumentConfig, ...] = (
        InstrumentConfig("XAUUSD", "GC=F",      0.01,  "metals"),
        InstrumentConfig("XAGUSD", "SI=F",      0.001, "metals"),
        InstrumentConfig("USDJPY", "USDJPY=X",  0.01,  "forex"),
        InstrumentConfig("GBPJPY", "GBPJPY=X",  0.01,  "forex"),
        InstrumentConfig("BTCUSD", "BTC-USD",   1.0,   "crypto"),
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
