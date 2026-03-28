import sys
import logging

def setup_logging(app):
    """
    Set up logging configuration for the entire app.
    To use, call logging.info()/debug()/whatever anywhere in the project.
    :param app: Flask app object
    """
    logger = logging.getLogger()

    # Log to stdout for Docker
    stream_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Redirect Gunicorn/Flask logs to root logger as well
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    logger.handlers.extend(gunicorn_logger.handlers)

    # set log level based on gunicorn setting
    logger.setLevel(gunicorn_logger.level)