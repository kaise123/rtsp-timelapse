#!/usr/bin/env python3
"""
Docker entrypoint: generate config.yaml from environment variables, then run timelapse.
Supports single camera (RTSP_URL) or multiple cameras (CAMERAS YAML).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml


def env(key: str, default: str | None = None) -> str | None:
    """Get environment variable."""
    return os.environ.get(key, default)


def env_list(key: str, default: list[str] | None = None) -> list[str]:
    """Get comma-separated env var as list."""
    val = env(key)
    if not val:
        return default or []
    return [t.strip() for t in val.split(",") if t.strip()]


def build_cameras_from_env() -> list[dict]:
    """Build cameras list from RTSP_URL or CAMERAS env var."""
    cameras_yaml = env("CAMERAS")
    if cameras_yaml:
        try:
            cameras_data = yaml.safe_load(cameras_yaml)
        except yaml.YAMLError as e:
            print(f"Error: CAMERAS must be valid YAML: {e}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(cameras_data, list):
            print("Error: CAMERAS must be a YAML list of cameras", file=sys.stderr)
            sys.exit(1)
        for i, cam in enumerate(cameras_data):
            if not isinstance(cam, dict):
                print(f"Error: CAMERAS[{i}] must be a mapping", file=sys.stderr)
                sys.exit(1)
            if not cam.get("rtsp_url") or not cam.get("output_path"):
                print(
                    f"Error: CAMERAS[{i}] must have rtsp_url and output_path",
                    file=sys.stderr,
                )
                sys.exit(1)
        return cameras_data

    # Single camera
    rtsp_url = env("RTSP_URL")
    if not rtsp_url:
        print("Error: RTSP_URL or CAMERAS is required", file=sys.stderr)
        sys.exit(1)
    return [
        {
            "rtsp_url": rtsp_url,
            "output_path": env("OUTPUT_PATH", "/data/timelapse"),
            "filename_pattern": env("FILENAME_PATTERN", "{date}_{time}.jpg"),
        }
    ]


def build_config_from_env() -> dict:
    """Build config dict from environment variables."""
    cameras = build_cameras_from_env()

    schedule_mode = env("SCHEDULE_MODE", "fixed")
    if schedule_mode not in ("fixed", "dynamic", "evenly_spaced"):
        print(
            "Error: SCHEDULE_MODE must be fixed, dynamic, or evenly_spaced",
            file=sys.stderr,
        )
        sys.exit(1)

    schedule: dict = {"mode": schedule_mode}

    if schedule_mode in ("fixed", "dynamic"):
        times = env_list("SCHEDULE_TIMES")
        if not times:
            print(
                f"Error: SCHEDULE_TIMES is required for mode '{schedule_mode}' (comma-separated)",
                file=sys.stderr,
            )
            sys.exit(1)
        schedule["times"] = times

    if schedule_mode == "evenly_spaced":
        n = env("IMAGES_PER_DAY")
        if not n or not n.isdigit() or int(n) < 1:
            print(
                "Error: IMAGES_PER_DAY (positive integer) is required for evenly_spaced mode",
                file=sys.stderr,
            )
            sys.exit(1)
        schedule["images_per_day"] = int(n)
        schedule["sunrise_offset"] = env("SUNRISE_OFFSET", "+0m")
        schedule["sunset_offset"] = env("SUNSET_OFFSET", "-0m")

    location = None
    if schedule_mode in ("dynamic", "evenly_spaced"):
        lat = env("LATITUDE")
        lon = env("LONGITUDE")
        loc_tz = env("LOCATION_TIMEZONE")
        if not lat or not lon or not loc_tz:
            print(
                "Error: LATITUDE, LONGITUDE, and LOCATION_TIMEZONE are required "
                f"for mode '{schedule_mode}'",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            location = {
                "latitude": float(lat),
                "longitude": float(lon),
                "timezone": loc_tz,
            }
        except ValueError:
            print("Error: LATITUDE and LONGITUDE must be numbers", file=sys.stderr)
            sys.exit(1)

    config = {
        "cameras": cameras,
        "timezone": env("TIMEZONE", "UTC"),
        "schedule": schedule,
    }

    if location:
        config["location"] = location

    return config


def main() -> None:
    config_path = Path("/tmp/config.yaml")
    config = build_config_from_env()

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Set TZ so container uses configured timezone (logs, system time, DST)
    # Use location timezone for dynamic/evenly_spaced, else TIMEZONE
    if config.get("location"):
        tz = config["location"]["timezone"]
    else:
        tz = config.get("timezone", "UTC")
    os.environ["TZ"] = tz

    # Run timelapse with generated config
    cmd = ["python", "timelapse.py", "--config", str(config_path)]
    log_level = env("LOG_LEVEL")
    if log_level:
        cmd.extend(["--log-level", log_level])
    os.execvp("python", cmd)


if __name__ == "__main__":
    main()
