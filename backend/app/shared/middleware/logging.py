import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def configure_logging(log_level: str) -> None:
    logging.basicConfig(format="%(message)s", level=log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        logger_factory=structlog.PrintLoggerFactory(),
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Stamps every request/response with a request id and logs duration + status.

    The request id is what lets you correlate a log line, a trace span, and (once
    the outbox/EDA phase lands) the event a request produced — across process
    boundaries once we extract microservices.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request_id_ctx.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        log = structlog.get_logger("http")
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            log.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
