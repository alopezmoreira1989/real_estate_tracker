"""structlog configuration: JSON in production, key-value in dev (CLAUDE.md #11)."""

import logging

import structlog

from real_estate.infrastructure.config.settings import Environment


def configure_logging(environment: Environment, log_level: str = "INFO") -> None:
    """Configure structlog once at process startup."""
    level = logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if environment is Environment.PROD
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
