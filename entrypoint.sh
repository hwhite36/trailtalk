#!/bin/bash
set -e

echo "Waiting for db to come up..."
sleep 5 # TODO add more sophisticated check

echo "Starting Gunicorn server..."
# TODO consider adding threads
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    main:app