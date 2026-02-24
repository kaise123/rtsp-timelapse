"""Configuration loading and validation for the RTSP timelapse application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CameraConfig:
    """Configuration for a single camera."""

    rtsp_url: str
    output_path: str
    filename_pattern: str = "{date}_{time}.jpg"

    @property
    def resolved_output_path(self) -> Path:
        """Return the output path expanded and resolved."""
        path = Path(self.output_path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class LocationConfig:
    """Location configuration for sunrise/sunset calculations."""

    latitude: float
    longitude: float
    timezone: str


@dataclass
class ScheduleConfig:
    """Schedule configuration."""

    mode: str  # "fixed" | "dynamic" | "evenly_spaced"
    times: list[str] = field(default_factory=list)
    images_per_day: int | None = None
    sunrise_offset: str = "+0m"
    sunset_offset: str = "-0m"


@dataclass
class TimelapseConfig:
    """Full timelapse configuration."""

    cameras: list[CameraConfig]
    schedule: ScheduleConfig
    location: LocationConfig | None = None
    timezone: str = "UTC"  # Used for fixed mode when location is not set

    @property
    def rtsp_url(self) -> str:
        """Legacy: return first camera's RTSP URL."""
        return self.cameras[0].rtsp_url if self.cameras else ""

    @property
    def output_path(self) -> str:
        """Legacy: return first camera's output path."""
        return self.cameras[0].output_path if self.cameras else ""

    @property
    def resolved_output_path(self) -> Path:
        """Legacy: return first camera's resolved output path."""
        return self.cameras[0].resolved_output_path if self.cameras else Path(".")


def _parse_schedule(data: dict) -> tuple[ScheduleConfig, "LocationConfig | None", str]:
    """Parse schedule, location, and timezone from config data."""
    schedule_data = data.get("schedule")
    if not schedule_data or not isinstance(schedule_data, dict):
        raise ValueError("config: 'schedule' is required and must be a mapping")

    mode = schedule_data.get("mode", "fixed")
    if mode not in ("fixed", "dynamic", "evenly_spaced"):
        raise ValueError(
            f"config: schedule.mode must be 'fixed', 'dynamic', or 'evenly_spaced', got '{mode}'"
        )

    times = schedule_data.get("times", [])
    if not isinstance(times, list):
        raise ValueError("config: schedule.times must be a list")
    times = [str(t) for t in times]

    images_per_day = schedule_data.get("images_per_day")
    if images_per_day is not None and (
        not isinstance(images_per_day, int) or images_per_day < 1
    ):
        raise ValueError("config: schedule.images_per_day must be a positive integer")

    sunrise_offset = schedule_data.get("sunrise_offset", "+0m")
    sunset_offset = schedule_data.get("sunset_offset", "-0m")
    if not isinstance(sunrise_offset, str):
        sunrise_offset = "+0m"
    if not isinstance(sunset_offset, str):
        sunset_offset = "-0m"

    schedule = ScheduleConfig(
        mode=mode,
        times=times,
        images_per_day=images_per_day,
        sunrise_offset=sunrise_offset,
        sunset_offset=sunset_offset,
    )

    # Location (required for dynamic and evenly_spaced)
    location = None
    loc_data = data.get("location")
    if mode in ("dynamic", "evenly_spaced"):
        if not loc_data or not isinstance(loc_data, dict):
            raise ValueError(
                f"config: 'location' (latitude, longitude, timezone) is required for schedule mode '{mode}'"
            )
        lat = loc_data.get("latitude")
        lon = loc_data.get("longitude")
        tz = loc_data.get("timezone")
        if lat is None or lon is None:
            raise ValueError("config: location.latitude and location.longitude are required")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("config: location.latitude and longitude must be numbers")
        if not tz or not isinstance(tz, str):
            raise ValueError("config: location.timezone is required and must be a string")
        location = LocationConfig(latitude=float(lat), longitude=float(lon), timezone=tz)
    elif loc_data and isinstance(loc_data, dict):
        lat = loc_data.get("latitude")
        lon = loc_data.get("longitude")
        tz = loc_data.get("timezone", "UTC")
        if lat is not None and lon is not None and tz:
            location = LocationConfig(
                latitude=float(lat), longitude=float(lon), timezone=str(tz)
            )

    timezone = data.get("timezone", "UTC")
    if not isinstance(timezone, str):
        timezone = "UTC"

    # Validate schedule consistency
    if mode == "fixed" and not times:
        raise ValueError("config: schedule.times is required for fixed mode")
    if mode == "dynamic" and not times:
        raise ValueError("config: schedule.times is required for dynamic mode")
    if mode == "evenly_spaced":
        if not images_per_day or images_per_day < 1:
            raise ValueError(
                "config: schedule.images_per_day is required for evenly_spaced mode"
            )

    return schedule, location, timezone


def load_config(config_path: str | Path) -> TimelapseConfig:
    """Load and validate configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("Config file is empty")

    schedule, location, timezone = _parse_schedule(data)

    # Parse cameras: either 'cameras' list or legacy rtsp_url + output_path
    cameras: list[CameraConfig] = []
    default_pattern = data.get("filename_pattern", "{date}_{time}.jpg")
    if not isinstance(default_pattern, str):
        default_pattern = "{date}_{time}.jpg"

    cameras_data = data.get("cameras")
    if cameras_data is not None:
        if not isinstance(cameras_data, list):
            raise ValueError("config: 'cameras' must be a list")
        for i, cam in enumerate(cameras_data):
            if not isinstance(cam, dict):
                raise ValueError(f"config: cameras[{i}] must be a mapping")
            url = cam.get("rtsp_url")
            out = cam.get("output_path")
            if not url or not isinstance(url, str):
                raise ValueError(f"config: cameras[{i}].rtsp_url is required")
            if not out or not isinstance(out, str):
                raise ValueError(f"config: cameras[{i}].output_path is required")
            pattern = cam.get("filename_pattern", default_pattern)
            if not isinstance(pattern, str):
                pattern = default_pattern
            cameras.append(
                CameraConfig(rtsp_url=url, output_path=out, filename_pattern=pattern)
            )

    if not cameras:
        # Legacy: single camera from rtsp_url and output_path
        rtsp_url = data.get("rtsp_url")
        output_path = data.get("output_path", "./timelapse")
        if not rtsp_url or not isinstance(rtsp_url, str):
            raise ValueError("config: 'rtsp_url' is required (or use 'cameras' list)")
        if not isinstance(output_path, str):
            raise ValueError("config: 'output_path' must be a string")
        cameras = [
            CameraConfig(
                rtsp_url=rtsp_url,
                output_path=output_path,
                filename_pattern=default_pattern,
            )
        ]

    return TimelapseConfig(
        cameras=cameras,
        schedule=schedule,
        location=location,
        timezone=timezone,
    )
