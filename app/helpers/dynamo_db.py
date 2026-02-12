import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_dynamodb.service_resource import Table

from app.config.settings import AWS_DEFAULT_REGION, AWS_DYNAMODB_PORT, AWS_LOCAL, DYNAMODB_TABLE
from app.helpers.functions import get_iso_8601_timestamp, json_to_sha256_hash

logger = logging.getLogger(__name__)


def get_dynamodb() -> DynamoDBServiceResource:
    """
    Initializes and returns a DynamoDB ServiceResource object.

    This function dynamically connects to either a local DynamoDB instance
    (for development with AWS SAM) or to the AWS cloud-based service.
    This behavior is controlled by the 'AWS_LOCAL' flag.

    Returns:
        DynamoDBServiceResource: A high-level boto3 ServiceResource object for DynamoDB.

    Raises:
        ClientError: If there is an issue connecting to the DynamoDB endpoint,
                     such as network problems or invalid credentials.
    """
    # init dynamodb
    try:
        # condition if working locally for development or not
        if AWS_LOCAL:
            logger.info("Connecting to locally running dynamodb")
            dynamodb = cast(
                "DynamoDBServiceResource",
                boto3.resource(
                    "dynamodb",
                    endpoint_url=f"http://localhost:{AWS_DYNAMODB_PORT}",
                    region_name=AWS_DEFAULT_REGION,
                ),
            )
        else:
            logger.info("Connecting to dynamodb on aws")
            dynamodb = cast("DynamoDBServiceResource", boto3.resource("dynamodb"))
    except ClientError:
        logger.exception("Error connecting dynamodb")
        raise
    else:
        return dynamodb


def get_dynamodb_table() -> Table:
    """
    Returns a high-level DynamoDB Table resource object for the specified table.

    This function acts as a factory, creating a boto3 Table resource object
    which provides a high-level, object-oriented interface for interacting
    with a specific DynamoDB table.

    Returns:
        DynamoDBTableResource: The boto3 Table resource object for the table
                               defined by DYNAMODB_TABLE.
    """
    dynamodb: DynamoDBServiceResource = get_dynamodb()
    return dynamodb.Table(DYNAMODB_TABLE)  # ty: ignore[unresolved-attribute]


def insert_dynamodb(payload: dict[str, Any]) -> tuple[dict[str, Any], HTTPStatus]:
    """
    Inserts a new print job into DynamoDB.

    Creates a new item from the given payload, generating a SHA-256 hash as the
    job ID and recording the current UTC timestamp as creation time. The job is
    initialized with status "open".

    Args:
        payload: The print job request payload to store.

    Returns:
        A tuple of (response_dict, http_status) where response_dict contains
        the job status, reportUrl, and timestamps. Returns HTTPStatus.ACCEPTED
        on success or HTTPStatus.INTERNAL_SERVER_ERROR on failure.
    """
    print_table = get_dynamodb_table()

    # set values
    created_timestamp = get_iso_8601_timestamp()
    sha256_sum = json_to_sha256_hash(payload)
    status = "open"

    item_to_put = {
        "job_id": sha256_sum,
        "created_timestamp_iso_8601": created_timestamp,
        "started_timestamp_iso_8601": "",
        "finished_timestamp_iso_8601": "",
        "message": "",
        "payload": payload,
        "status": status,
    }

    logger.info(item_to_put)
    try:
        logger.info("Put to dynamodb")
        put_response = print_table.put_item(Item=item_to_put)
        logger.info(put_response)
    except ClientError:
        logger.exception("Error updating dynamodb")
        return ({"error": "Error updating dynamodb"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    return (
        {
            "status": status,
            "reportUrl": f"/jobs/{sha256_sum}",
            "created": created_timestamp,
            "started": "",
            "finished": "",
        },
        HTTPStatus.ACCEPTED,
    )


def status_print(job_id: str | None) -> tuple[dict[str, Any], HTTPStatus]:
    """
    Retrieves the current status of a print job from DynamoDB.

    Looks up the job by its ID and returns its status, report URL,
    and timestamps (created, started, finished).

    Args:
        job_id: The SHA-256 hash identifying the print job, or None.

    Returns:
        A tuple of (response_dict, http_status) where response_dict contains
        the job details. Returns HTTPStatus.OK if found,
        HTTPStatus.NOT_FOUND if no matching job exists, or
        HTTPStatus.INTERNAL_SERVER_ERROR on DynamoDB errors.
    """
    print_table = get_dynamodb_table()
    try:
        print_queued = print_table.get_item(Key={"job_id": job_id})
        if "Item" in print_queued:
            item = print_queued["Item"]
            return (
                {
                    "status": item["status"],
                    "reportUrl": f"/jobs/{item['job_id']}",
                    "created": item["created_timestamp_iso_8601"],
                    "started": item["started_timestamp_iso_8601"],
                    "finished": item["finished_timestamp_iso_8601"],
                },
                HTTPStatus.OK,
            )
        return ({"warning": f"No entry found for job id {job_id}"}, HTTPStatus.NOT_FOUND)  # noqa: TRY300
    except ClientError:
        logger.exception("warning no print job found")
        return ({"error": "Error while looking for job_id"}, HTTPStatus.INTERNAL_SERVER_ERROR)
