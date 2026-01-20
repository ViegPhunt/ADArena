#!/bin/bash -e

/await_start.sh

cd /app

python -m workers.worker