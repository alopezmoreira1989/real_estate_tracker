import structlog

from real_estate.infrastructure.config.settings import Environment
from real_estate.infrastructure.logging import configure_logging


def test_configure_logging_dev_does_not_raise() -> None:
    configure_logging(Environment.DEV)

    structlog.get_logger("test").info("hello", key="value")


def test_configure_logging_prod_does_not_raise() -> None:
    configure_logging(Environment.PROD, log_level="DEBUG")

    structlog.get_logger("test").info("hello", key="value")
