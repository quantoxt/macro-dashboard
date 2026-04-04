"""
Telegram Message Formatter
===========================
Formats signals and outcomes into readable Telegram messages.
Uses Markdown parse_mode (bold, italic, code).
"""

from datetime import datetime, timezone
from typing import Any


def _direction_emoji(direction: str) -> str:
    return "🟢" if direction == "BUY" else "🔴"


def _format_price(value: Any, instrument: str) -> str:
    """Format price based on instrument type."""
    try:
        price = float(value)
        if instrument in ("XAUUSD", "XAGUSD"):
            return f"{price:.2f}"
        elif instrument in ("USDJPY", "GBPJPY"):
            return f"{price:.3f}"
        elif instrument == "BTCUSD":
            return f"{price:,.0f}"
        else:
            return f"{price:.5f}"
    except (ValueError, TypeError):
        return str(value)


def format_signal_batch(signals: list[dict]) -> str:
    """Format multiple signals into a single Telegram message."""
    if not signals:
        return ""

    lines: list[str] = []

    if len(signals) == 1:
        sig = signals[0]
        lines.append("🚨 *New Signal*\n")
        lines.append(_format_single_signal(sig))
    else:
        lines.append(f"🚨 *{len(signals)} New Signals*\n")
        for i, sig in enumerate(signals, 1):
            lines.append(_format_single_signal(sig, compact=True))
            if i < len(signals):
                lines.append("")

    return "\n".join(lines)


def _format_single_signal(sig: dict, compact: bool = False) -> str:
    """Format a single signal dict into Telegram message lines."""
    inst = sig.get("instrument", "???")
    direction = sig.get("direction", "???")
    strategy = sig.get("strategy", "???")
    confidence = sig.get("confidence", 0)

    lines: list[str] = []
    lines.append(f"{_direction_emoji(direction)} *{inst}* — {direction}")

    if not compact:
        lines.append(f"  Strategy: {strategy}")
        lines.append(f"  Confidence: {confidence}%")

    lines.append(
        f"  Entry: `{_format_price(sig.get('entry'), inst)}` "
        f"→ SL: `{_format_price(sig.get('stopLoss'), inst)}` "
        f"→ TP: `{_format_price(sig.get('takeProfit'), inst)}`"
    )

    rr = sig.get("riskReward", 0)
    lines.append(f"  R:R: {rr} | Confidence: {confidence}%")

    if not compact:
        reasons = sig.get("reasons", [])
        if reasons:
            top_reasons = reasons[:3]
            lines.append(f"  _{', '.join(top_reasons)}_")

    return "\n".join(lines)


def format_outcome(signal: dict, outcome: str, pnl_pips: float | None = None) -> str:
    """Format an outcome notification.

    Example output:
    ✅ XAUUSD BUY (Confluence) → WIN +45 pips
    ❌ BTCUSD SELL (Momentum) → LOSS -23 pips
    ⏰ GBPJPY SELL (Mean Reversion) → EXPIRED
    """
    inst = signal.get("instrument", "???")
    direction = signal.get("direction", "???")
    strategy = signal.get("strategy", "???")

    if outcome == "WIN":
        emoji = "✅"
        pnl_str = f"+{pnl_pips:.1f} pips" if pnl_pips is not None else ""
    elif outcome == "LOSS":
        emoji = "❌"
        pnl_str = f"{pnl_pips:.1f} pips" if pnl_pips is not None else ""
    else:  # EXPIRED
        emoji = "⏰"
        pnl_str = "no fill"

    line = f"{emoji} *{inst}* {direction} ({strategy}) → *{outcome}*"
    if pnl_str:
        line += f" {pnl_str}"

    # Add notes if any
    notes = signal.get("notes", "")
    if notes:
        line += f"\n_\"{notes[:100]}\"_"

    # Add manual entry/exit if taken
    user_status = signal.get("userStatus", "auto")
    if user_status == "taken":
        manual_entry = signal.get("manualEntry")
        manual_exit = signal.get("manualExit")
        if manual_entry is not None:
            line += f"\nEntry: `{_format_price(manual_entry, inst)}`"
        if manual_exit is not None:
            line += f" → Exit: `{_format_price(manual_exit, inst)}`"

    return line
