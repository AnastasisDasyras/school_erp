import asyncio
import logging

import structlog

from reporting.config import get_settings
from reporting.consumer import run_consumer


def main() -> None:
    settings = get_settings()
    logging.basicConfig(format="%(message)s", level=settings.log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )
    asyncio.run(run_consumer(settings))


if __name__ == "__main__":
    main()
