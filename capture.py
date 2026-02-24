"""RTSP frame capture using OpenCV."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0


def capture_frame(
    rtsp_url: str,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> "np.ndarray | None":
    """
    Capture a single frame from an RTSP stream.

    Args:
        rtsp_url: The RTSP URL of the camera stream.
        retries: Number of capture attempts on failure.
        retry_delay: Seconds to wait between retries.

    Returns:
        The captured frame as a numpy array (BGR), or None on failure.
    """
    for attempt in range(1, retries + 1):
        cap = None
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                logger.warning(
                    "Failed to open RTSP stream (attempt %d/%d): %s",
                    attempt,
                    retries,
                    rtsp_url,
                )
                if attempt < retries:
                    time.sleep(retry_delay)
                continue

            ret, frame = cap.read()
            cap.release()
            cap = None

            if ret and frame is not None:
                return frame

            logger.warning(
                "Failed to read frame from RTSP stream (attempt %d/%d)",
                attempt,
                retries,
            )

        except Exception as e:
            logger.exception("Error capturing frame: %s", e)
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

        if attempt < retries:
            time.sleep(retry_delay)

    logger.error("All %d capture attempts failed for %s", retries, rtsp_url)
    return None
