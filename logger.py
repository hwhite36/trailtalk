import sys
import logging

def setup_logging(app):
    """
    Set up logging configuration for the entire app.
    To use, call logging.info()/debug()/whatever anywhere in the project.
    :param app: Flask app object
    """
    logger = logging.getLogger()

    # Prevent duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    # Log to stdout for Docker
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Sync Flask's app logger with the root logger
    app.logger.handlers = logger.handlers
    app.logger.propagate = True

    # Set log level based on Gunicorn's setting
    gunicorn_logger = logging.getLogger('gunicorn.error')
    logger.setLevel(gunicorn_logger.level)