import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_dynamodb.service_resource import Table

from app.config.settings import (
    AWS_CONNECT_TIMEOUT,
    AWS_DEFAULT_REGION,
    AWS_LOCAL,
    AWS_READ_TIMEOUT,
    DYNAMODB_TABLE_NAME,
    LOCALSTACK_PORT,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
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
    boto_config = Config(
        connect_timeout=AWS_CONNECT_TIMEOUT,
        read_timeout=AWS_READ_TIMEOUT,
    )
    try:
        # condition if working locally for development
        if AWS_LOCAL:
            logger.info("Connecting to locally running dynamodb")
            dynamodb = cast(
                "DynamoDBServiceResource",
                boto3.resource(
                    "dynamodb",
                    endpoint_url=f"http://localhost:{LOCALSTACK_PORT}",
                    region_name=AWS_DEFAULT_REGION,
                    config=boto_config,
                ),
            )
        else:
            dynamodb = cast(
                "DynamoDBServiceResource", boto3.resource("dynamodb", config=boto_config)
            )
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
                               defined by DYNAMODB_TABLE_NAME.
    """
    dynamodb: DynamoDBServiceResource = get_dynamodb()
    return dynamodb.Table(DYNAMODB_TABLE_NAME)  # ty: ignore[unresolved-attribute]


def insert_dynamodb(item: dict[str, Any]) -> None:
    """
    Inserts a pre-built print job item into DynamoDB.

    Args:
        item: The complete DynamoDB item dict containing job_id, timestamps,
              status, payload, and message fields.

    Raises:
        ClientError: If there is an issue inserting the item into DynamoDB.
    """
    dynamodb_table = get_dynamodb_table()

    logger.info(item)
    try:
        logger.info("Put to dynamodb")
        dynamodb_table.put_item(Item=item)
        logger.debug("Put job %s into DynamoDB (status=%s)", item["job_id"], item["status"])
    except ClientError:
        logger.exception("Error updating dynamodb")
        raise


def get_print_job(job_id: str | None) -> dict[str, Any] | None:
    """
    Retrieves a print job item from DynamoDB.

    Args:
        job_id: The SHA-256 hash identifying the print job, or None.

    Returns:
        The DynamoDB item dict if found, or None if no matching job exists.

    Raises:
        ClientError: If there is an issue querying DynamoDB.
    """
    dynamodb_table = get_dynamodb_table()
    try:
        print_queued = dynamodb_table.get_item(Key={"job_id": job_id})
    except ClientError:
        logger.exception("Error looking up print job %s", job_id)
        raise
    if "Item" in print_queued:
        return dict(print_queued["Item"])
    return None
