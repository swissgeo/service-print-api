"""OpenTelemetry metrics for the print API.

The instruments are created at import time from the global meter provider set up
in app.otel. When metrics are disabled (no provider configured) they resolve to
no-op proxies, so the ``record_*`` helpers are always safe to call.

Request volume and status/outcome splits for POST /jobs and GET /jobs/{job_id}
are intentionally NOT custom metrics: the default
``http.server.request.duration`` from the FastAPI instrumentation already carries
``http.route`` and ``http.response.status_code``, from which those counts are
derivable.

Queue state (backlog, DLQ arrivals) is deliberately not measured here either — it
comes from CloudWatch, see METRICS.md §1 and §4 in the renderer repo.

``scope.version`` (METRICS_SCHEMA_VERSION) is the version of the metric schema
emitted under this scope — bump it on any schema change (semver).
"""

from opentelemetry import metrics

METRICS_SCHEMA_VERSION = "1.0.0"
meter = metrics.get_meter(__name__, METRICS_SCHEMA_VERSION)

# The same instrument name is defined in the renderer (scope app.helpers.metrics),
# which emits every other outcome. Name, unit and description must stay identical
# across the two scopes, or Prometheus sees conflicting HELP text for one series.
_jobs = meter.create_counter(
    "swissgeo.service_print.jobs",
    unit="{job}",
    description="Print jobs, labelled by lifecycle outcome",
)


def record_job_created() -> None:
    """Count a job accepted and enqueued, once per job.

    Not recorded for a deduplicated re-request, which returns a job already counted
    on its original request, nor when the enqueue itself failed.
    """
    _jobs.add(1, {"outcome": "created"})
