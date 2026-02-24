#!/usr/bin/env python3
"""
RTSP Timelapse - Capture frames from an RTSP camera stream at configurable times.

Supports fixed times, sunrise/sunset-based dynamic times, and evenly-spaced
captures between sunrise and sunset. Can run as a standalone script or as a
system service on Linux (systemd) or Windows (Task Scheduler / NSSM).
Supports multiple cameras, each saving to a different folder.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime

import cv2

from capture import capture_frame
from config import load_config
from scheduler import get_next_capture_time

logger = logging.getLogger(__name__)

HOUR = 3600


def setup_logging(level: str = "INFO") -> None:
    """Configure logging to stdout."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def format_filename(pattern: str, capture_time: datetime) -> str:
    """Format the filename pattern with date and time placeholders."""
    return pattern.format(
        date=capture_time.strftime("%Y-%m-%d"),
        time=capture_time.strftime("%H-%M-%S"),
        datetime=capture_time.strftime("%Y-%m-%d_%H-%M-%S"),
    )


def _sleep_with_hourly_log(
    next_time: datetime, sleep_seconds: float
) -> None:
    """Sleep until next capture, logging every hour when the next image will be saved."""
    while sleep_seconds > 0:
        chunk = min(HOUR, sleep_seconds)
        time.sleep(chunk)
        now = datetime.now(next_time.tzinfo)
        sleep_seconds = (next_time - now).total_seconds()
        if sleep_seconds > 0:
            logger.info(
                "Next image will be saved at %s (in %.1f seconds)",
                next_time.strftime("%Y-%m-%d %H:%M:%S"),
                sleep_seconds,
            )


def run(config_path: str | Path) -> None:
    """Main run loop: schedule captures and save frames for all cameras."""
    config = load_config(config_path)
    output_dirs = [cam.resolved_output_path for cam in config.cameras]

    logger.info(
        "Starting RTSP timelapse with %d camera(s). Output: %s",
        len(config.cameras),
        ", ".join(str(p) for p in output_dirs),
    )
    logger.info("Schedule mode: %s", config.schedule.mode)

    while True:
        next_time = get_next_capture_time(config)
        now = datetime.now(next_time.tzinfo)
        sleep_seconds = (next_time - now).total_seconds()

        if sleep_seconds > 0:
            logger.info("Next capture at %s (in %.1f seconds)", next_time, sleep_seconds)
            _sleep_with_hourly_log(next_time, sleep_seconds)

        # Capture and save for each camera
        for i, camera in enumerate(config.cameras):
            frame = capture_frame(camera.rtsp_url)
            if frame is None:
                logger.error(
                    "Skipping capture for camera %d (%s) - failed to get frame",
                    i + 1,
                    camera.output_path,
                )
                continue

            output_dir = camera.resolved_output_path
            filename = format_filename(camera.filename_pattern, next_time)
            filepath = output_dir / filename
            if cv2.imwrite(str(filepath), frame):
                logger.info("Saved: %s", filepath)
            else:
                logger.error("Failed to save: %s", filepath)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="RTSP Timelapse - Capture frames at configurable times"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        run(args.config)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except ValueError as e:
        logger.error("Config error: %s", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
