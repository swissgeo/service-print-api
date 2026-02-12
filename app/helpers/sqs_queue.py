import json
import logging
from typing import TYPE_CHECKING, Any

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

from app.config.settings import AWS_DEFAULT_REGION, AWS_LOCAL, AWS_PORT, SQS_QUEUE_NAME

logger = logging.getLogger(__name__)


def get_sqs_client() -> SQSClient:
    """
    Initializes and returns an SQS client object.

    This function dynamically connects to either a local SQS instance
    (via LocalStack for development) or to the AWS cloud-based service.
    This behavior is controlled by the 'AWS_LOCAL' flag.

    Returns:
        SQSClient: A boto3 SQS client object.

    Raises:
        ClientError: If there is an issue connecting to the SQS endpoint,
                     such as network problems or invalid credentials.
    """
    try:
        if AWS_LOCAL:
            logger.info("Connecting to locally running SQS")
            sqs = boto3.client(
                "sqs",
                endpoint_url=f"http://localhost:{AWS_PORT}",
                region_name=AWS_DEFAULT_REGION,
            )
        else:
            logger.info("Connecting to SQS on AWS")
            sqs = boto3.client("sqs")
    except ClientError:
        logger.exception("Error connecting to SQS")
        raise
    else:
        return sqs


def send_to_queue(message: dict[str, Any]) -> None:
    """
    Sends a message to the SQS queue.

    Serializes the given message dict to JSON and sends it to the
    queue defined by SQS_QUEUE_NAME.

    Args:
        message: The message dict to send (typically the full DynamoDB item).

    Raises:
        ClientError: If there is an issue sending the message to SQS.
    """
    sqs = get_sqs_client()
    try:
        queue_url = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)["QueueUrl"]
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )
        logger.info("Message sent to SQS queue %s", SQS_QUEUE_NAME)
    except ClientError:
        logger.exception("Error sending message to SQS queue %s", SQS_QUEUE_NAME)
        raise
