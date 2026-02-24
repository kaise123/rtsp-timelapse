FROM python:3.12-slim

# Install tzdata for timezone support (DST, IANA zones)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py scheduler.py sun.py capture.py timelapse.py ./
COPY docker-entrypoint.py ./

# Output directory for captured images
RUN mkdir -p /data/timelapse

ENTRYPOINT ["python", "docker-entrypoint.py"]
