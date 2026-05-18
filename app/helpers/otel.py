import logging

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from fastapi import FastAPI

from app.config.settings import get_settings

# Resource.create() reads OTEL_RESOURCE_ATTRIBUTES from the environment automatically.
_resource = Resource.create()


def _setup_providers() -> tuple[LoggerProvider | None, TracerProvider | None]:
    settings = get_settings()

    if settings.otel_sdk_disabled:
        return None, None

    log_provider = LoggerProvider(resource=_resource)
    set_logger_provider(log_provider)

    trace_provider = TracerProvider(resource=_resource)
    trace.set_tracer_provider(trace_provider)

    return log_provider, trace_provider


def _setup_exporters(
    log_provider: LoggerProvider | None,
    trace_provider: TracerProvider | None,
) -> None:
    settings = get_settings()

    if settings.otel_sdk_disabled or trace_provider is None:
        return

    endpoint = settings.otel_exporter_otlp_endpoint
    insecure = settings.otel_exporter_otlp_insecure
    headers = settings.otel_exporter_otlp_headers or None

    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=insecure, headers=headers))
    )

    if settings.otel_enable_logging and log_provider is not None:
        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=endpoint, insecure=insecure, headers=headers)
            )
        )


# ---------------------------------------------------------------------------
# Import-time setup.
# No lazy imports needed — uvicorn has no monkey-patching constraints.
# ---------------------------------------------------------------------------
log_provider, trace_provider = _setup_providers()
_setup_exporters(log_provider, trace_provider)


def get_otel_handler() -> logging.Handler:
    """Return the OTEL logging handler for use in a logging YAML config."""
    if log_provider is None:
        raise ValueError("OTEL log provider is not initialised (OTEL_SDK_DISABLED=true?)")
    return LoggingHandler(logger_provider=log_provider)


def initialize_instrumentation(app: FastAPI) -> None:
    """Instrument FastAPI and botocore."""
    settings = get_settings()

    if settings.otel_sdk_disabled:
        return

    if settings.otel_enable_botocore:
        BotocoreInstrumentor().instrument()
    if settings.otel_enable_fastapi:
        FastAPIInstrumentor.instrument_app(app)


def shutdown_otel() -> None:
    """Flush and shutdown OTEL providers."""
    if trace_provider is not None:
        trace_provider.shutdown()
    if log_provider is not None:
        log_provider.shutdown()
