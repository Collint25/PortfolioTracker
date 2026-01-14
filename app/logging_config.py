"""Logging configuration for Portfolio Tracker."""

import logging
import sys


def configure_logging() -> None:
    """
    Configure logging to capture SDK warnings in stdout.

    Sets up a root logger with INFO level and adds a stream handler
    to output logs to stdout. This ensures SnapTrade SDK warnings
    and other log messages are visible in the console.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    # Set specific loggers
    logging.getLogger("snaptrade_client").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("Logging configured")
