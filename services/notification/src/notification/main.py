import asyncio
import logging

import structlog

from notification.config import get_settings
from notification.consumer import run_consumer
from notification.email import SesEmailSender
from notification.tracing import setup_tracing


def main() -> None:
    setup_tracing()
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
    email = SesEmailSender(settings)
    asyncio.run(run_consumer(settings, email))


if __name__ == "__main__":
    main()
