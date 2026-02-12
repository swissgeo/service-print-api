import logging
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_dynamodb.service_resource import Table

from app.config.settings import (
    AWS_DEFAULT_REGION,
    AWS_LOCAL,
    AWS_PROFILE,
    DYNAMODB_TABLE_NAME,
    LOCALSTACK_PORT,
)

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
        # condition if working locally for development
        if AWS_LOCAL == "local":
            logger.info("Connecting to locally running dynamodb")
            dynamodb = cast(
                "DynamoDBServiceResource",
                boto3.resource(
                    "dynamodb",
                    endpoint_url=f"http://localhost:{LOCALSTACK_PORT}",
                    region_name=AWS_DEFAULT_REGION,
                ),
            )
        # condition if working locally using the dynamodb and sqs on the poc account
        # TODO can be deleted when not using poc account anymore
        elif AWS_LOCAL == "aws_poc":
            logger.info("Your current profile is '%s'", AWS_PROFILE)
            logger.info("Connecting to dynamodb on aws poc account")
            session = boto3.Session(profile_name=AWS_PROFILE)
            dynamodb = cast("DynamoDBServiceResource", session.resource("dynamodb"))
        else:
            session = boto3.Session()
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
        put_response = dynamodb_table.put_item(Item=item)
        logger.info(put_response)
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
