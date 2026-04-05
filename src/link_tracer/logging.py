"""Logging configuration for link-tracer."""

from __future__ import annotations

import logging
import sys

import structlog
from rich.console import Console


def configure_debug_logging(enabled: bool) -> None:
    """Configure structlog for debug output.

    When enabled, configures JSON-formatted structured logging at DEBUG level.
    When disabled, sets level to CRITICAL to suppress all output.

    Args:
        enabled: Whether to enable debug logging.
    """
    level = logging.DEBUG if enabled else logging.CRITICAL
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_console(verbose: bool) -> Console:
    """Return a rich.Console configured for verbose or quiet mode.

    Args:
        verbose: When True, writes to stdout for CliRunner capture.
            When False, uses quiet mode.

    Returns:
        Configured rich.Console instance.
    """
    if verbose:
        return Console(file=sys.stdout, force_terminal=True)
    return Console(quiet=True)
