import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE_ENV = "LOG_FILE"
LOG_LEVEL_ENV = "LOG_LEVEL"

DEFAULT_LOG_FILE = "/app/logs/app.log"
DEFAULT_LOG_LEVEL = "INFO"

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

_FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_STREAM_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

_configured = False


def setup_logging() -> None:
    """Configure stdlib logging with a rotating file handler and a stdout stream handler.

    Sentry's LoggingIntegration (configured in app.py) hooks into the same stdlib
    logging records, so every record emitted here is also forwarded to Rustrak/Sentry.
    Safe to call multiple times; only the first call has an effect.
    """
    global _configured
    if _configured:
        return

    log_file = os.environ.get(LOG_FILE_ENV, DEFAULT_LOG_FILE)
    log_level_name = os.environ.get(LOG_LEVEL_ENV, DEFAULT_LOG_LEVEL).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(logging.Formatter(_STREAM_FORMAT))
    root.addHandler(stream_handler)

    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        root.addHandler(file_handler)
    except OSError:
        # E.g. local dev without a writable /app/logs: keep stdout + Sentry
        # logging working instead of crashing the app.
        root.warning("Log file %s is not writable; logging to stdout only", log_file)

    _configured = True
