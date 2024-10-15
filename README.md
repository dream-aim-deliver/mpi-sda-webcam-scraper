# mpi-sda-webcam-scraper

## Description

This is a scraper repo that scrapes data from a live webcam and a weather api as well

### Run the container

```bash
docker build -t mpi-webcam-scraper .
```

```bash
docker run --rm \
    --name mpi-webcam-scraper \
    --net="host" \
    mpi-webcam-scraper
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

1. screenshots images from a webcam URL at regular intervals

```bash
python webcam_scraper.py
```

2. scrapes weather data for the webcam location

```bash
python API_scraper.py
```
