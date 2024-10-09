```bash
docker build -t mpi-webcam-scraper .



docker run --rm \
    --name mpi-webcam-scraper \
    --net="host" \
    mpi-webcam-scraper
```
