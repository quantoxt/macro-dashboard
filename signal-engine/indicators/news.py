"""
Economic Calendar & News Auto-Pause
=====================================
Fetches economic calendar events, detects high-impact events,
and provides auto-pause logic for signal generation.

Primary source: https://nfs.faireconomy.media/ff_calendar_thisweek.json
Fallback: empty calendar (never block signals on fetch failure).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# The 13 key US announcements to watch
HIGH_IMPACT_KEYWORDS = [
    "nonfarm", "non-farm", "nfp", "employment change",
    "cpi", "consumer price", "inflation",
    "gdp", "gross domestic",
    "fomc", "fed rate", "interest rate",
    "retail sales",
    "ppi", "producer price",
    "durable goods",
    "philly fed",
    "consumer confidence", "cci",
    "home sales", "housing",
    "chicago pmi",
    "trade balance",
    "unemployment",
]

# Currencies we care about (matches our instruments)
WATCHED_CURRENCIES = {"USD", "JPY", "GBP"}


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    country: str
    date_str: str  # raw date from API
    impact: str  # "High", "Medium", "Low"
    currency: str = ""


@dataclass
class NewsPauseResult:
    pause_active: bool
    reason: str
    upcoming_high_impact: list[CalendarEvent]
    session: str  # "ASIAN", "EUROPEAN", "US"


def _is_high_impact(event: CalendarEvent) -> bool:
    """Check if event is one of the 13 key announcements."""
    title_lower = event.title.lower()
    return any(kw in title_lower for kw in HIGH_IMPACT_KEYWORDS)


def get_current_session() -> str:
    """Return current trading session based on UTC hour."""
    hour = datetime.now(timezone.utc).hour
    if 0 <= hour < 7:
        return "ASIAN"
    elif 7 <= hour < 13:
        return "EUROPEAN"
    else:
        return "US"


async def fetch_economic_calendar() -> list[CalendarEvent]:
    """Fetch this week's economic calendar from ForexFactory RSS.

    Never raises — returns empty list on failure.
    """
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    events: list[CalendarEvent] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()

        for item in data:
            impact = item.get("impact", "")
            title = item.get("title", "")
            country = item.get("country", "")
            date_str = item.get("date", "")
            currency = country  # ForexFactory uses country as currency proxy

            events.append(CalendarEvent(
                title=title,
                country=country,
                date_str=date_str,
                impact=impact,
                currency=currency,
            ))

        logger.debug("Fetched %d calendar events", len(events))

    except Exception as exc:
        logger.warning("Failed to fetch economic calendar: %s", exc)

    return events


def _parse_event_datetime(date_str: str) -> datetime | None:
    """Parse event date string to UTC datetime."""
    if not date_str:
        return None
    try:
        # ForexFactory format: "2026-04-02T13:30:00-04:00"
        dt = datetime.fromisoformat(date_str)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def check_news_pause(
    events: list[CalendarEvent],
    pause_minutes: int = 15,
) -> NewsPauseResult:
    """Check if signal generation should be paused due to upcoming/recent news.

    Pause window: `pause_minutes` before and after each high-impact event
    that affects our watched currencies.
    """
    now = datetime.now(timezone.utc)
    upcoming_high: list[CalendarEvent] = []
    pause_active = False
    reason = ""

    for event in events:
        # Only care about high-impact events
        if event.impact != "High":
            continue

        # Check if event affects our currencies
        currency = event.currency.upper()
        if currency not in WATCHED_CURRENCIES and currency != "":
            # Also check if it's US-related (affects everything)
            if "US" not in currency and "USD" not in currency:
                continue

        event_time = _parse_event_datetime(event.date_str)
        if event_time is None:
            continue

        diff = (event_time - now).total_seconds() / 60  # minutes

        # Within pause window: X min before to X min after
        if -pause_minutes <= diff <= pause_minutes:
            pause_active = True
            if diff > 0:
                reason = f"High-impact event '{event.title}' in {diff:.0f} min"
            else:
                reason = f"High-impact event '{event.title}' {abs(diff):.0f} min ago"
            upcoming_high.append(event)

        # Track upcoming events within 2 hours
        if 0 < diff <= 120:
            upcoming_high.append(event)

    session = get_current_session()

    return NewsPauseResult(
        pause_active=pause_active,
        reason=reason,
        upcoming_high_impact=upcoming_high,
        session=session,
    )
