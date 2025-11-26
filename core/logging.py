import logging
import sys

from core.config import config

# Map string log levels to logging constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def setup_logging() -> logging.Logger:
    """
    Configure application logging with file name and line number.

    Default log level is INFO. SQL logs only show when LOG_LEVEL=DEBUG.
    """
    log_level = LOG_LEVELS.get(config.LOG_LEVEL.upper(), logging.INFO)

    # Create formatter with filename and line number
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Third-party loggers - reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # SQLAlchemy - only show SQL text at DEBUG level to avoid leaking PII in logs
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if log_level <= logging.DEBUG:
        sqlalchemy_logger.setLevel(logging.DEBUG)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)
