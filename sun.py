"""Sunrise/sunset calculations using the astral library."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from astral import LocationInfo
from astral.sun import sun
from zoneinfo import ZoneInfo


def get_sun_events(
    latitude: float, longitude: float, timezone_str: str, target_date: date
) -> dict[str, datetime]:
    """
    Get sun event times (dawn, sunrise, noon, sunset, dusk) for a given date and location.

    Returns a dict with keys: dawn, sunrise, noon, sunset, dusk.
    All times are timezone-aware in the location's timezone.
    """
    tz = ZoneInfo(timezone_str)
    location = LocationInfo(
        name="Camera",
        region="",
        timezone=timezone_str,
        latitude=latitude,
        longitude=longitude,
    )
    s = sun(location.observer, date=target_date, tzinfo=tz)
    return {
        "dawn": s["dawn"],
        "sunrise": s["sunrise"],
        "noon": s["noon"],
        "sunset": s["sunset"],
        "dusk": s["dusk"],
    }


def parse_offset(offset_str: str) -> timedelta:
    """
    Parse an offset string like '+30m', '-1h', '+90m' into a timedelta.

    Supports: +30m, -1h, +90m, -45m, +2h
    """
    offset_str = offset_str.strip()
    if not offset_str:
        return timedelta(0)

    match = re.match(r"^([+-]?)(\d+)([mh])$", offset_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid offset format: '{offset_str}'. Use e.g. +30m, -1h")

    sign_str, num_str, unit = match.groups()
    sign = -1 if sign_str == "-" else 1
    num = int(num_str)

    if unit.lower() == "m":
        delta = timedelta(minutes=num)
    else:  # h
        delta = timedelta(hours=num)

    return sign * delta


def parse_dynamic_time(
    spec: str, events: dict[str, datetime], target_date: date
) -> datetime:
    """
    Parse a dynamic time specification like 'sunrise+30m', 'noon', 'sunset-1h'
    into a datetime for the given date.

    Supported events: dawn, sunrise, noon, sunset, dusk
    Offset syntax: +30m, -1h, +90m (optional, defaults to +0m)
    """
    spec = spec.strip().lower()
    if not spec:
        raise ValueError("Empty time specification")

    # Map event names to keys in events dict
    event_names = ("dawn", "sunrise", "noon", "sunset", "dusk")
    offset_str = ""

    for name in event_names:
        if spec == name:
            base_time = events[name]
            break
        if spec.startswith(name):
            rest = spec[len(name) :].strip()
            if rest and rest[0] in "+-":
                base_time = events[name]
                offset_str = rest
                break
            elif not rest:
                base_time = events[name]
                break
    else:
        raise ValueError(
            f"Unknown time specification: '{spec}'. "
            f"Use one of: dawn, sunrise, noon, sunset, dusk (with optional +30m, -1h offset)"
        )

    if offset_str:
        delta = parse_offset(offset_str)
        return base_time + delta
    return base_time
