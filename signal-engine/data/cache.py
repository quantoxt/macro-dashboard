"""
Simple In-Memory OHLC Cache
============================
TTL-based cache to avoid hammering Yahoo Finance on every request.
"""

import logging
import time
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class DataCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def _key(self, ticker: str, interval: str) -> str:
        return f"{ticker}:{interval}"

    def get(self, ticker: str, interval: str) -> pd.DataFrame | None:
        key = self._key(ticker, interval)
        entry = self._store.get(key)
        if entry is None:
            return None

        expires_at, data = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None

        logger.debug("Cache hit: %s", key)
        return data

    def set(
        self, ticker: str, interval: str, data: pd.DataFrame, ttl: int
    ) -> None:
        key = self._key(ticker, interval)
        self._store[key] = (time.monotonic() + ttl, data)
        logger.debug("Cache set: %s (TTL=%ds)", key, ttl)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)
