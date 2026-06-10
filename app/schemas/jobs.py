from enum import StrEnum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from app.settings import get_settings


class JobStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
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
    state: str = Field(
        description="The map state. This can be a URL to the state or the state in base64"
    )

    @field_validator("state")
    @classmethod
    def validate_state_length(cls, v: str) -> str:
        max_len = get_settings().max_character_size_of_state
        if len(v) > max_len:
            raise ValueError(f"State must not exceed {max_len} characters")
        return v


class JobResponse(BaseModel):
    """Returned by POST /jobs (202 or 200) and GET /jobs/{job_id} (200)."""

    status: JobStatus
    reportPath: str = Field(description="Path to poll for this job's status")  # noqa: N815
    created: AwareDatetime = Field(description="ISO 8601 UTC creation timestamp")
    started: AwareDatetime | None = None
    finished: AwareDatetime | None = None
    pdfPath: str | None = None  # noqa: N815
    message: str | None = None


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
