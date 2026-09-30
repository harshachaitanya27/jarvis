"""Logging and OpenTelemetry configuration.

Two concerns, kept separate:

- ``configure_logging`` sets up the stdlib logging tree — a single stdout
  handler, a level from settings, and text or JSON formatting. Always applied.
- ``configure_telemetry`` wires OpenTelemetry (logs, traces, metrics) and
  auto-instruments FastAPI, SQLAlchemy, and httpx. Only when OTEL_ENABLED, so
  local dev and tests need no collector.

Application code just calls ``logging.getLogger(__name__)`` and logs normally;
both the stdout handler and (when enabled) the OTel exporter pick it up.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from app.config import Settings

# Library loggers routed through our root handler instead of their own.
_MANAGED_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "sqlalchemy.engine",
    "apscheduler",
    "httpx",
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with trace correlation when present."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Injected by LoggingInstrumentor when a span is active.
        for src, dst in (("otelTraceID", "trace_id"), ("otelSpanID", "span_id")):
            value = getattr(record, src, None)
            if value and value != "0" * len(value):
                payload[dst] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s")
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Let managed libraries propagate to the root handler rather than duplicate.
    for name in _MANAGED_LOGGERS:
        lib = logging.getLogger(name)
        lib.handlers = []
        lib.propagate = True
    # SQLAlchemy's echo logs at INFO; keep them out unless explicitly debugging.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def configure_telemetry(app, settings: Settings) -> None:
    """Wire OTel logs/traces/metrics and instrument the app. No-op if disabled."""
    if not settings.otel_enabled:
        return

    from opentelemetry import metrics, trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import (
        BatchLogRecordProcessor,
        ConsoleLogExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.service_version,
            "deployment.environment": settings.app_env,
        }
    )
    console = settings.otel_console_export
    base = settings.otel_exporter_otlp_endpoint.rstrip("/")

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = (
        ConsoleSpanExporter()
        if console
        else OTLPSpanExporter(endpoint=f"{base}/v1/traces")
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_exporter = (
        ConsoleMetricExporter()
        if console
        else OTLPMetricExporter(endpoint=f"{base}/v1/metrics")
    )
    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(metric_exporter)],
        )
    )

    # Logs — export stdlib log records through OTel as well.
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = (
        ConsoleLogExporter()
        if console
        else OTLPLogExporter(endpoint=f"{base}/v1/logs")
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(
        LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    )

    # Instrument. LoggingInstrumentor injects trace/span ids onto log records.
    LoggingInstrumentor().instrument(set_logging_format=False)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    from app.adapters.db.session import engine

    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    logging.getLogger("app").info(
        "OpenTelemetry enabled (console=%s, endpoint=%s)",
        console,
        base,
    )
