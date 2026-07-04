from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from app.shared.observability.metrics import http_request_duration_seconds, http_requests_total


def _route_pattern(request: Request) -> str:
    """Return the matched route pattern (e.g. /api/v1/students/{student_id})
    instead of the concrete path — avoids cardinality explosion in Prometheus
    when IDs appear in the URL.

    Only concrete `Route` objects carry a `.path`; mounted sub-routers added via
    `include_router` surface as `Mount`/`_IncludedRouter` with no `.path`, so we
    guard with `getattr` and fall back to the concrete URL path rather than 500.
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            path = getattr(route, "path", None)
            if path is not None:
                return path
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Records http_requests_total and http_request_duration_seconds for every
    request that passes through. Runs after RequestContextMiddleware so the
    request-id is already set.

    Using the route *pattern* (not the concrete path) as a label is critical:
    without it, every unique student_id creates a new label combination and
    Prometheus cardinality explodes.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        route = _route_pattern(request)
        method = request.method
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        status = str(response.status_code)

        http_requests_total.labels(method=method, route=route, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, route=route).observe(duration)

        return response
