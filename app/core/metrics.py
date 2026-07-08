"""OpenTelemetry metrics for the print API.

The instrument is created at import time from the global meter provider set up in
app.otel. When metrics are disabled (no provider configured) it resolves to a
no-op proxy, so the ``record_*`` helper is always safe to call.

Only queue depth is a custom instrument here. Request volume and status/outcome
splits for POST /jobs and GET /jobs/{job_id} are intentionally NOT custom
metrics: the default ``http.server.duration`` from the FastAPI instrumentation
already carries ``http.route`` and ``http.response.status_code``, from which
those counts are derivable.

``scope.version`` (METRICS_SCHEMA_VERSION) is the version of the metric schema
emitted under this scope — bump it on any schema change (semver).
"""

from opentelemetry import metrics

METRICS_SCHEMA_VERSION = "1.0.0"
meter = metrics.get_meter(__name__, METRICS_SCHEMA_VERSION)

# Sampled whenever POST /jobs checks the queue length for overload protection, so
# it reuses the SQS read already made — no extra AWS calls. Only updated while
# print requests arrive; CloudWatch remains the continuous source of truth.
_queue_depth = meter.create_gauge(
    "swissgeo.service_print.queue.depth",
    unit="{message}",
    description="Approximate number of messages in the SQS print queue",
)


def record_queue_depth(length: int) -> None:
    """Record the approximate SQS queue depth."""
    _queue_depth.set(length)
