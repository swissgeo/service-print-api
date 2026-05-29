import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from botocore.exceptions import ClientError
from opentelemetry import trace

from fastapi import APIRouter, Body, HTTPException, Response

from app.core.dynamo_db import get_print_job, insert_dynamodb
from app.core.sqs_queue import is_queue_overloaded, send_to_queue
from app.core.utils import (
    dict_to_sha256_hash,
    get_hours_difference,
    get_ttl_timestamp,
    validate_payload,
)
from app.dependencies import SessionDep
from app.schemas.errors import ErrorResponse
from app.schemas.jobs import DBJobItem, JobResponse, JobStatus
from app.settings import get_settings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

router = APIRouter()


def _to_job_response(item: DBJobItem) -> JobResponse:
    """Build a JobResponse from a DBJobItem."""
    return JobResponse(
        status=item.status,
        reportUrl=f"{get_settings().api_path_prefix}/jobs/{item.job_id}",
        created=item.created_timestamp_iso_8601,
        started=item.started_timestamp_iso_8601,
        finished=item.finished_timestamp_iso_8601,
        pdfUrl=item.pdf_url,
        message=item.message,
    )


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=202,
    responses={
        200: {"model": JobResponse},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def start_print(
    session: SessionDep,
    response: Response,
    payload: Annotated[Any, Body()] = None,
) -> JobResponse:
    with tracer.start_as_current_span("api.start_print"):
        try:
            validate_payload(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        job_id = dict_to_sha256_hash(payload)

        try:
            existing = await get_print_job(job_id, session)
        except ClientError:
            logger.exception("Error getting item from dynamodb")
            existing = None

        if existing is not None and existing.status != JobStatus.ERROR:
            now = datetime.now(UTC).isoformat()
            if (
                get_hours_difference(existing.created_timestamp_iso_8601.isoformat(), now)
                < get_settings().expiration_time_hh_print_doc
            ):
                logger.info("Returning already registered print request")
                response.status_code = 200
                return _to_job_response(existing)

        if await is_queue_overloaded(session):
            logger.warning("SQS queue is overloaded, rejecting new print job")
            raise HTTPException(
                status_code=503, detail="Service overloaded, please try again later"
            )

        created_ts = datetime.now(UTC)
        item: dict[str, Any] = {
            "job_id": job_id,
            "created_timestamp_iso_8601": created_ts.isoformat(),
            "ttl": get_ttl_timestamp(),
            "payload": payload,
            "status": JobStatus.OPEN,
        }

        try:
            await insert_dynamodb(item, session)
        except ClientError:
            logger.exception("Error inserting item into DynamoDB")
            raise HTTPException(
                status_code=500, detail="Error storing print job in database"
            ) from None

        try:
            await send_to_queue(item, session)
        except ClientError:
            logger.exception("Error sending item to SQS queue")
            raise HTTPException(
                status_code=500, detail="Error sending print job to queue"
            ) from None

        return JobResponse(
            status=JobStatus.OPEN,
            reportUrl=f"{get_settings().api_path_prefix}/jobs/{job_id}",
            created=created_ts,
        )


@router.get(
    "/jobs",
    response_model=ErrorResponse,
    status_code=501,
)
async def print_list() -> None:
    raise HTTPException(status_code=501, detail="Print job listing has not been implemented")


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def print_status(job_id: str, session: SessionDep) -> JobResponse:
    with tracer.start_as_current_span("api.print_status"):
        try:
            item = await get_print_job(job_id, session)
        except ClientError:
            raise HTTPException(status_code=500, detail="Error while looking for job_id") from None
        if item is None:
            raise HTTPException(status_code=404, detail=f"No entry found for job id {job_id}")
        return _to_job_response(item)
