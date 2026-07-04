"""Process entry point: `python -m real_estate`. Wired to the CLI once presentation/cli exists."""

import structlog

from real_estate.infrastructure.config.settings import Settings
from real_estate.infrastructure.logging import configure_logging


def main() -> None:
    settings = Settings()
    configure_logging(settings.environment, settings.log_level)
    structlog.get_logger(__name__).info(
        "real_estate_placeholder_start", detail="CLI not yet wired, see roadmap Phase 7"
    )


if __name__ == "__main__":
    main()
