import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, cast

LOG_FILE_ENV = "LOG_FILE"
LOG_LEVEL_ENV = "LOG_LEVEL"

DEFAULT_LOG_FILE = "/app/logs/app.log"
DEFAULT_LOG_LEVEL = "INFO"

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

_FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_STREAM_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

_configured = False


class KvLogger(logging.Logger):
    """Logger that accepts structlog-style named arguments.

    Keyword arguments are rendered as `key=value` pairs appended to the
    message, e.g. `logger.info("Query executed", user="a@b.ch", duration_ms=42)`
    logs `Query executed user=a@b.ch duration_ms=42`. The same fields are also
    attached to the LogRecord as `extra`, so the Sentry/Rustrak
    LoggingIntegration forwards them as searchable attributes.
    """

    def _render(self, msg: str, args: tuple, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fields = " ".join(f"{key}={value}" for key, value in kwargs.items())
        message = f"{msg} {fields}" if fields else msg
        return message, kwargs

    def _log_with_kwargs(self, level: int, msg: str, args: tuple, kwargs: dict[str, Any]) -> None:
        message, extra = self._render(msg, args, kwargs)
        if self.isEnabledFor(level):
            self._log(
                level,
                message,
                args,
                exc_info=kwargs.pop("exc_info", None),
                extra=extra,
                stack_info=False,
                stacklevel=1,
            )

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_with_kwargs(logging.DEBUG, msg, args, kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_with_kwargs(logging.INFO, msg, args, kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_with_kwargs(logging.WARNING, msg, args, kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_with_kwargs(logging.ERROR, msg, args, kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_with_kwargs(logging.CRITICAL, msg, args, kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self._log_with_kwargs(logging.ERROR, msg, args, kwargs)


def get_logger(name: str) -> KvLogger:
    """Return a KvLogger under the app's logger namespace."""
    logger = logging.getLogger(f"dataspot_facade_api.{name}")
    if isinstance(logger, KvLogger):
        return logger
    # getLogger only returns KvLogger once setup_logging() has swapped in the
    # KvLogger class; recreate the logger if it was cached as a plain Logger.
    logging.root.manager.loggerDict.pop(f"dataspot_facade_api.{name}", None)
    logging.setLoggerClass(KvLogger)
    return cast(KvLogger, logging.getLogger(f"dataspot_facade_api.{name}"))


def setup_logging() -> None:
    """Configure stdlib logging with a rotating file handler and a stdout stream handler.

    Sentry's LoggingIntegration (configured in app.py) hooks into the same stdlib
    logging records, so every record emitted here is also forwarded to Rustrak/Sentry.
    Safe to call multiple times; only the first call has an effect.
    """
    global _configured
    if _configured:
        return

    logging.setLoggerClass(KvLogger)
    # Re-create the app's loggers so they use KvLogger (setLoggerClass only
    # affects loggers created afterwards).
    for logger_name in list(logging.root.manager.loggerDict):
        if logger_name.startswith("dataspot_facade_api"):
            del logging.root.manager.loggerDict[logger_name]

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
