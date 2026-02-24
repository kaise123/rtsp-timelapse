# RTSP Timelapse

Capture single frames from RTSP camera streams at configurable times to create a timelapse. Supports **multiple cameras** (each in its own folder), fixed times, sunrise/sunset-based scheduling, and evenly-spaced captures. Uses a configurable timezone with automatic daylight saving time (DST) handling.

## Quick Start (Single Camera)

```bash
docker run -d \
  -e RTSP_URL=rtsp://user:pass@192.168.1.100:554/stream \
  -e SCHEDULE_MODE=fixed \
  -e SCHEDULE_TIMES=08:00,12:00,18:00 \
  -e TIMEZONE=Europe/London \
  -v timelapse-data:/data \
  --name rtsp-timelapse \
  kaise123/rtsp-timelapse:latest
```

## Docker Compose (Multiple Cameras)

Create `docker-compose.yml`:

```yaml
services:
  timelapse:
    image: kaise123/rtsp-timelapse:latest
    container_name: rtsp-timelapse
    restart: unless-stopped
    environment:
      CAMERAS: |
        - rtsp_url: rtsp://user:password@192.168.1.100:554/front
          output_path: /data/front
        - rtsp_url: rtsp://user:password@192.168.1.101:554/back
          output_path: /data/back
      SCHEDULE_MODE: dynamic
      SCHEDULE_TIMES: sunrise+30m,noon,sunset-1h
      LATITUDE: 51.5074
      LONGITUDE: -0.1278
      LOCATION_TIMEZONE: Europe/London
    volumes:
      - timelapse-data:/data

volumes:
  timelapse-data:
```

Run with `docker compose up -d`. Each camera saves to its own folder under `/data`.

## Logging

While waiting for the next capture, the service logs every hour with the scheduled save time:

```
Next image will be saved at 2025-02-23 14:30:00 (in 3600.0 seconds)
```

## Timezone

The container uses a configurable timezone. Set it via `TIMEZONE` (fixed mode) or `LOCATION_TIMEZONE` (dynamic/evenly_spaced). Use IANA timezone names (e.g. `Europe/London`, `America/New_York`). Daylight saving time is handled automatically.

```yaml
# Fixed mode
TIMEZONE: Europe/London

# Dynamic/evenly_spaced (also sets container timezone)
LOCATION_TIMEZONE: Europe/London
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RTSP_URL` | Yes* | Single camera: RTSP stream URL |
| `OUTPUT_PATH` | No | Single camera: output dir (default: `/data/timelapse`) |
| `CAMERAS` | Yes* | Multiple cameras: YAML list with `rtsp_url` and `output_path` per camera |
| `SCHEDULE_MODE` | Yes | `fixed`, `dynamic`, or `evenly_spaced` |
| `SCHEDULE_TIMES` | Yes (fixed/dynamic) | Comma-separated times |
| `IMAGES_PER_DAY` | Yes (evenly_spaced) | Number of images per day |
| `LATITUDE`, `LONGITUDE`, `LOCATION_TIMEZONE` | Yes (dynamic/evenly_spaced) | Location for sunrise/sunset |
| `TIMEZONE` | No | Timezone for fixed mode (default: `UTC`) |
| `FILENAME_PATTERN` | No | Pattern with `{date}`, `{time}` |
| `SUNRISE_OFFSET`, `SUNSET_OFFSET` | No | For evenly_spaced |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

\* Use `RTSP_URL` for one camera, or `CAMERAS` for multiple.

## Schedule Modes

- **fixed** – Capture at explicit times (e.g. `08:00,12:00,18:00`)
- **dynamic** – Capture relative to sun events: `sunrise+30m`, `noon`, `sunset-1h`, `dawn`, `dusk`
- **evenly_spaced** – N images evenly distributed between sunrise and sunset

## Persisting Images

Mount at `/data` so all camera folders are persisted:

```bash
-v timelapse-data:/data
# or
-v /path/on/host:/data
```

Each camera's images go to its `output_path` (e.g. `/data/front`, `/data/back`).

## License

MIT
