from enum import StrEnum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field


class JobStatus(StrEnum):
    """Status of a print job.

    - `open`: job submitted successfully to the print queue
    - `started`: renderer has started processing the job
    - `finished`: rendering complete; document is ready for download
    - `error`: rendering failed
    """

    OPEN = "open"
    STARTED = "started"
    FINISHED = "finished"
    ERROR = "error"


class PrintJobPayload(BaseModel):
    """Body accepted by POST /jobs."""

    print_format: Literal["a0", "a1", "a2", "a3", "a4", "a5", "a6"] = Field(
        description="Paper format"
    )
    print_orientation: Literal["portrait", "landscape"] = Field(description="Page orientation")
    print_resolution: int = Field(ge=72, le=300, description="Resolution in DPI")
    print_scale: int | None = Field(
        default=None, ge=1, le=5_000_000, description="Map scale denominator"
    )
    state_id: str = Field(
        pattern=r"^[0-9a-f]{16}$",
        description="SHA-256-derived identifier for the map state (16 lowercase hex characters)",
    )


class JobResponse(BaseModel):
    """Returned by POST /jobs (202 or 200) and GET /jobs/{job_id} (200)."""

    status: JobStatus
    reportUrl: str = Field(description="URL to poll for this job's status")  # noqa: N815
    created: AwareDatetime = Field(description="ISO 8601 UTC creation timestamp")
    started: AwareDatetime | None = Field(
        default=None, description="Timestamp when the renderer started processing"
    )
    finished: AwareDatetime | None = Field(
        default=None, description="Timestamp when rendering completed"
    )
    pdfUrl: str | None = Field(  # noqa: N815
        default=None, description="URL to the rendered PDF; set when status is finished"
    )
    message: str | None = Field(default=None, description="Optional status or error message")


class DBJobItem(BaseModel):
    """Internal representation of a DynamoDB print-job item."""

    job_id: str
    status: JobStatus
    payload: dict[str, Any]
    created_timestamp_iso_8601: AwareDatetime
    started_timestamp_iso_8601: AwareDatetime | None = None
    finished_timestamp_iso_8601: AwareDatetime | None = None
    pdf_path: str | None = None
    message: str | None = None
    ttl: int | None = None
