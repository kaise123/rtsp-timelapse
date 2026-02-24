"""Schedule calculation for fixed, dynamic, and evenly_spaced capture modes."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import TimelapseConfig
from sun import get_sun_events, parse_dynamic_time


def _get_all_capture_times_today(config: TimelapseConfig, target_date: date) -> list[datetime]:
    """Get all capture times for a given date."""
    schedule = config.schedule
    tz = (
        ZoneInfo(config.location.timezone)
        if config.location
        else ZoneInfo(config.timezone)
    )

    if schedule.mode == "fixed":
        times: list[datetime] = []
        for t_str in schedule.times:
            parts = t_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            t = time(hour, minute, second)
            dt = datetime.combine(target_date, t, tzinfo=tz)
            times.append(dt)
        return sorted(times)

    if schedule.mode == "dynamic":
        if not config.location:
            return []
        events = get_sun_events(
            config.location.latitude,
            config.location.longitude,
            config.location.timezone,
            target_date,
        )
        times = []
        for spec in schedule.times:
            try:
                dt = parse_dynamic_time(spec, events, target_date)
                times.append(dt)
            except (ValueError, KeyError):
                continue
        return sorted(times)

    if schedule.mode == "evenly_spaced":
        if not config.location or not schedule.images_per_day:
            return []
        events = get_sun_events(
            config.location.latitude,
            config.location.longitude,
            config.location.timezone,
            target_date,
        )
        from sun import parse_offset

        sunrise_offset = parse_offset(schedule.sunrise_offset)
        sunset_offset = parse_offset(schedule.sunset_offset)
        start = events["sunrise"] + sunrise_offset
        end = events["sunset"] + sunset_offset
        if start >= end:
            return []
        n = schedule.images_per_day
        if n == 1:
            return [start + (end - start) / 2]
        delta = (end - start) / (n - 1)
        times = [start + delta * i for i in range(n)]
        return sorted(times)

    return []


def get_next_capture_time(config: TimelapseConfig, now: datetime | None = None) -> datetime:
    """
    Get the next capture time based on the current configuration.

    Returns the next datetime at which a frame should be captured.
    If no captures remain today, returns the first capture time for the next day.
    """
    tz = (
        ZoneInfo(config.location.timezone)
        if config.location
        else ZoneInfo(config.timezone)
    )
    if now is None:
        now = datetime.now(tz)

    # Ensure now is timezone-aware in our location's tz
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    today = now.date()
    times_today = _get_all_capture_times_today(config, today)
    for dt in times_today:
        if dt > now:
            return dt

    # No more today; get first capture tomorrow
    tomorrow = today + timedelta(days=1)
    times_tomorrow = _get_all_capture_times_today(config, tomorrow)
    if times_tomorrow:
        return times_tomorrow[0]

    # Edge case: no captures at all (e.g. polar winter)
    # Return now + 24h to avoid busy loop
    return now + timedelta(days=1)
