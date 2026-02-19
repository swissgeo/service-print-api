from os import getenv
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.helpers.utils import strtobool

if TYPE_CHECKING:
    from flask import Flask


def initialize() -> None:
    """Initialize OTEL instrumentation for logging and botocore.

    Should be called before the Flask app is created so that boto3/ssl are
    instrumented before they are imported. Controlled by env vars:
    - OTEL_SDK_DISABLED: disables all instrumentation when true
    - OTEL_ENABLE_LOGGING: enables LoggingInstrumentor when true
    - OTEL_ENABLE_BOTOCORE: enables BotocoreInstrumentor when true
    """
    if not strtobool(getenv("OTEL_SDK_DISABLED", "false")):
        if strtobool(getenv("OTEL_ENABLE_LOGGING", "false")):
            LoggingInstrumentor().instrument()
        if strtobool(getenv("OTEL_ENABLE_BOTOCORE", "false")):
            BotocoreInstrumentor().instrument()


def initialize_flask(app: Flask) -> None:
    """Instrument the Flask app with OTEL tracing.

    Should be called after the app is created. Controlled by env vars:
    - OTEL_SDK_DISABLED: disables all instrumentation when true
    - OTEL_ENABLE_FLASK: enables FlaskInstrumentor when true
    """
    if not strtobool(getenv("OTEL_SDK_DISABLED", "false")) and strtobool(
        getenv("OTEL_ENABLE_FLASK", "false")
    ):
        FlaskInstrumentor().instrument_app(app)


def setup_trace_provider() -> None:
    """Configure and register the OTLP trace provider.

    Should be called in the gunicorn post_fork hook so each worker gets its
    own tracer provider. Controlled by env vars:
    - OTEL_SDK_DISABLED: disables all instrumentation when true
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    - OTEL_EXPORTER_OTLP_HEADERS: optional headers for the exporter
    - OTEL_EXPORTER_OTLP_INSECURE: use insecure (plaintext) connection when true
    """
    if not strtobool(getenv("OTEL_SDK_DISABLED", "false")):
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
                headers=getenv("OTEL_EXPORTER_OTLP_HEADERS"),
                insecure=strtobool(getenv("OTEL_EXPORTER_OTLP_INSECURE", "false")),
            )
        )
        provider = TracerProvider(resource=Resource.create())
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)
