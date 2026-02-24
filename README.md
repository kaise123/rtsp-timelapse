# RTSP Timelapse

Capture single frames from an RTSP camera stream at configurable times to create a timelapse. Supports fixed times, sunrise/sunset-based dynamic scheduling, and evenly-spaced captures throughout the day.

## Features

- **Multiple cameras**: Add multiple RTSP cameras, each saving to its own folder
- **Configurable times**: Fixed times (e.g., 08:00, 12:00, 18:00) or multiple times per day
- **Number of images per day**: Control how many frames to capture (via `times` list or `images_per_day`)
- **Sunrise/sunset support**: Schedule captures relative to dawn, sunrise, noon, sunset, dusk with offsets (e.g., `sunrise+30m`, `sunset-1h`)
- **Cross-platform**: Run as a script or service on Linux and Windows
- **Hourly status logs**: Logs when the next image will be saved every hour while waiting

## Requirements

- Python 3.9+
- RTSP camera or stream

## Installation

```bash
cd TimeLapse
pip install -r requirements.txt
```

## Configuration

1. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml`:
   - Single camera: set `rtsp_url` and `output_path`
   - Multiple cameras: set `cameras` list with `rtsp_url` and `output_path` per camera
   - Configure schedule (fixed, dynamic, or evenly_spaced)
   - For dynamic/evenly_spaced modes, set your location (latitude, longitude, timezone)

### Schedule Modes

| Mode | Description |
|------|-------------|
| **fixed** | Explicit times in 24h format: `["08:00", "12:00", "18:00"]` |
| **dynamic** | Sunrise/sunset events with offsets: `["sunrise+30m", "noon", "sunset-1h"]` |
| **evenly_spaced** | N images evenly distributed between sunrise and sunset |

### Dynamic Time Syntax

- Events: `dawn`, `sunrise`, `noon`, `sunset`, `dusk`
- Offsets: `+30m`, `-1h`, `+90m` (add or subtract from the event time)

## Docker

Run as a container with configuration via environment variables:

```bash
docker compose up -d
```

Edit `docker-compose.yml` to set your variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `RTSP_URL` | Yes* | Single camera: RTSP stream URL |
| `OUTPUT_PATH` | No | Single camera: output directory (default: `/data/timelapse`) |
| `CAMERAS` | Yes* | Multiple cameras: YAML list with `rtsp_url` and `output_path` per camera |
| `SCHEDULE_MODE` | Yes | `fixed`, `dynamic`, or `evenly_spaced` |
| `SCHEDULE_TIMES` | Yes (fixed/dynamic) | Comma-separated times |
| `IMAGES_PER_DAY` | Yes (evenly_spaced) | Number of images per day |
| `LATITUDE`, `LONGITUDE`, `LOCATION_TIMEZONE` | Yes (dynamic/evenly_spaced) | Location for sunrise/sunset |
| `FILENAME_PATTERN` | No | Filename pattern (default: `{date}_{time}.jpg`) |
| `TIMEZONE` | No | Timezone for fixed mode (default: `UTC`) |
| `SUNRISE_OFFSET`, `SUNSET_OFFSET` | No (evenly_spaced) | Offsets |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

\* Use either `RTSP_URL` (single camera) or `CAMERAS` (multiple cameras).

Captured images are stored in the `timelapse-data` volume. Mount at `/data` so all camera folders (e.g. `/data/front`, `/data/back`) are persisted:

```yaml
volumes:
  - timelapse-data:/data
```

Or use a host directory: `- /path/on/host:/data`

The Docker image logs the next capture time every hour while waiting.

## Usage

### Run as Script

```bash
python timelapse.py
```

With custom config path:

```bash
python timelapse.py --config /path/to/config.yaml
```

With debug logging:

```bash
python timelapse.py --log-level DEBUG
```

### Run as Service

#### Linux (systemd)

1. Copy the service file:
   ```bash
   sudo cp systemd/timelapse.service /etc/systemd/system/
   ```

2. Edit the service file and set `WorkingDirectory` and `ExecStart` to your installation path:
   ```
   WorkingDirectory=/path/to/TimeLapse
   ExecStart=/usr/bin/python3 /path/to/TimeLapse/timelapse.py --config /path/to/TimeLapse/config.yaml
   ```

3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable timelapse
   sudo systemctl start timelapse
   sudo systemctl status timelapse
   ```

#### Windows

Use Task Scheduler or NSSM to run the script at startup. See `windows/install-service.ps1` for setup instructions.

## Output

Images are saved to each camera's `output_path` using its `filename_pattern`. Default pattern `{date}_{time}.jpg` produces files like `2025-02-23_08-30-00.jpg`.
