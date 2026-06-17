import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from botocore.exceptions import ClientError

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.dynamo_db import get_print_job, insert_dynamodb
from app.core.sqs_queue import is_queue_overloaded, send_to_queue
from app.dependencies import SessionDep
from app.schemas.errors import ErrorResponse
from app.schemas.jobs import DBJobItem, JobResponse, JobStatus, PrintJobPayload
from app.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def dict_to_sha256_hash(data: dict[str, object]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_ttl_timestamp() -> int:
    settings = get_settings()
    now_utc = datetime.now(UTC)
    return int((now_utc + timedelta(hours=settings.ttl_dynamodb_item_hh)).timestamp())


def get_hours_difference(start_date_str: str, end_date_str: str) -> float:
    try:
        start = datetime.fromisoformat(start_date_str)
        end = datetime.fromisoformat(end_date_str)
        return (end - start).total_seconds() / 3600
    except ValueError as e:
        logger.exception("Invalid date format. Please use ISO 8601")
        raise ValueError("Invalid date format. Please use ISO 8601") from e


def _to_job_response(item: DBJobItem, request: Request) -> JobResponse:
    """Build a JobResponse from a DBJobItem."""
    settings = get_settings()
    base_url = str(request.base_url).rstrip("/")
    return JobResponse(
        status=item.status,
        reportUrl=f"{base_url}{settings.api_path_prefix}/jobs/{item.job_id}",
        created=item.created_timestamp_iso_8601,
        started=item.started_timestamp_iso_8601,
        finished=item.finished_timestamp_iso_8601,
        pdfUrl=f"{base_url}{item.pdf_path}" if item.pdf_path else None,
        message=item.message,
    )


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=202,
    tags=["Jobs"],
    summary="Submit a new print job",
    responses={
        200: {"model": JobResponse},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def start_print(
    session: SessionDep,
    request: Request,
    response: Response,
    payload: PrintJobPayload,
) -> JobResponse:
    settings = get_settings()
    payload_dict = payload.model_dump()
    job_id = dict_to_sha256_hash(payload_dict)

    try:
        existing = await get_print_job(job_id, session)
    except ClientError:
        logger.exception("Error getting item from dynamodb")
        existing = None

    if existing is not None and existing.status != JobStatus.ERROR:
        now = datetime.now(UTC).isoformat()
        if (
            get_hours_difference(existing.created_timestamp_iso_8601.isoformat(), now)
            < settings.expiration_time_hh_print_doc
        ):
            logger.info("Returning already registered print request")
            response.status_code = 200
            return _to_job_response(existing, request)

    if await is_queue_overloaded(session):
        logger.warning("SQS queue is overloaded, rejecting new print job")
        raise HTTPException(status_code=503, detail="Service overloaded, please try again later")

    created_ts = datetime.now(UTC)
    item: dict[str, Any] = {
        "job_id": job_id,
        "created_timestamp_iso_8601": created_ts.isoformat(),
        "ttl": get_ttl_timestamp(),
        "payload": payload_dict,
        "status": JobStatus.OPEN,
    }

    try:
        await insert_dynamodb(item, session)
    except ClientError:
        logger.exception("Error inserting item into DynamoDB")
        raise HTTPException(status_code=500, detail="Error storing print job in database") from None

    try:
        await send_to_queue(item, session)
    except ClientError:
        logger.exception("Error sending item to SQS queue")
        raise HTTPException(status_code=500, detail="Error sending print job to queue") from None

    base_url = str(request.base_url).rstrip("/")
    return JobResponse(
        status=JobStatus.OPEN,
        reportUrl=f"{base_url}{settings.api_path_prefix}/jobs/{job_id}",
        created=created_ts,
    )


@router.get(
    "/jobs",
    response_model=ErrorResponse,
    status_code=501,
    tags=["Jobs"],
    summary="List print jobs (not implemented)",
)
async def print_list() -> None:
    raise HTTPException(status_code=501, detail="Print job listing has not been implemented")


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Get the status of a print job",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def print_status(job_id: str, session: SessionDep, request: Request) -> JobResponse:
    try:
        item = await get_print_job(job_id, session)
    except ClientError:
        raise HTTPException(status_code=500, detail="Error while looking for job_id") from None
    if item is None:
        raise HTTPException(status_code=404, detail=f"No entry found for job id {job_id}")
    return _to_job_response(item, request)
