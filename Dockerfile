FROM python:3.14-slim

# TODO set PYTHONUNBUFFERED=1
# TODO set gunicorn log level to info, and tell gunicorn to send logs to stdout/stderr:
    # --log-level info \
    # --access-logfile - \
    # --error-logfile - \