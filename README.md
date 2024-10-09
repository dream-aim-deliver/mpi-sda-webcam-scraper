```bash
docker build -t mpi-telegram-scraper .



docker run --rm \
    --name mpi-webcam-scraper \
    --net="host" \
    mpi-webcam-scraper
```