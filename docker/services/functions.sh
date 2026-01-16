#!/bin/bash -e

start_web() {
  echo "[*] Starting web service $1"
  cd /app
  gunicorn "api.$1:app" \
    --bind "0.0.0.0:${PORT:-5000}" \
    --log-level "${LOG_LEVEL:-INFO}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 1
}

start_api() {
  start_web public
}

start_admin() {
  start_web admin
}

start_events() {
  start_web events
}

start_http_receiver() {
  echo "[*] Starting http_receiver service"
  cd /app
  python3 -m api.monitoring
}

start_ticker() {
  echo "[*] Starting ticker"
  cd /app
  python3 -m workers.ticker
}

start_worker() {
  echo "[*] Starting Arq worker with ${CHECKERS:-1} checker(s), max ${JOBS:-1} jobs"
  cd /app
  python -m workers.worker
}