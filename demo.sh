#!/usr/bin/env bash

python webcam_scraper.py --roundshot_webcam_id "5e568898681458.46669392" \
    --start_date "2024-09-15T09:00" \
    --end_date "2024-09-15T12:00" \
    --interval "60" \
    --latitude "35.652832" \
    --longitude "139.839478" \
    --log-level="INFO" \
    --case-study-name "disaster_tracker" \
    --tracer-id "argentina" --job-id "13" \
    --kp_auth_token test123 --kp_host localhost --kp_port 8000 --kp_scheme http 
