"""Tracer access for hand-written spans.

Thin wrapper over the OTel API so services don't import ``opentelemetry``
directly. ``trace.get_tracer`` returns a no-op tracer when no provider is
configured (OTEL_ENABLED off), so spans are cheap no-ops in dev and tests and
become real once telemetry is enabled.

Manual spans cover the background generation pipeline — which runs as a job, not
inside an HTTP request, so the FastAPI request instrumentation doesn't reach it.
Request-scoped work (auth, onboarding, library, feedback) is already traced by
that automatic instrumentation.
"""

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

__all__ = ["get_tracer", "Status", "StatusCode"]


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
