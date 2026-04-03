from .base import BaseStrategy, Signal
from .confluence_breakout import ConfluenceBreakout
from .consolidation_detector import detect_consolidation, detect_breakout, ConsolidationResult

__all__ = ["BaseStrategy", "Signal", "ConfluenceBreakout", "detect_consolidation", "detect_breakout"]
