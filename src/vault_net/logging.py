"""Debug and console logging configuration."""

import logging

import structlog
from rich.console import Console


def configure_debug_logging(enabled: bool) -> None:
    """Configure structlog for debug logging.

    Args:
        enabled: Whether to enable debug logging. When False, logging is
            effectively disabled by setting the level to CRITICAL.
    """
    level = logging.DEBUG if enabled else logging.CRITICAL

    logging.basicConfig(
        format="%(message)s",
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_console(verbose: bool) -> Console:
    """Return a configured Rich console.

    Args:
        verbose: When True, writes to stdout for CliRunner capture.
            When False, returns a quiet console.

    Returns:
        A configured Rich Console instance.
    """
    return Console(quiet=not verbose)
