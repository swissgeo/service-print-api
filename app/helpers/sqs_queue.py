import json
import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

from app.config.settings import (
    AWS_CONNECT_TIMEOUT,
    AWS_LOCAL,
    AWS_READ_TIMEOUT,
    AWS_REGION,
    MOTO_ENDPOINT,
    SQS_QUEUE_MAX_LENGTH,
    SQS_QUEUE_NAME,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
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
    boto_config = Config(
        connect_timeout=AWS_CONNECT_TIMEOUT,
        read_timeout=AWS_READ_TIMEOUT,
    )
    try:
        if AWS_LOCAL:
            logger.info("Connecting to locally running SQS")
            sqs = boto3.client(
                "sqs",
                endpoint_url=MOTO_ENDPOINT,
                region_name=AWS_REGION,
                config=boto_config,
            )
        else:
            sqs = boto3.client("sqs", config=boto_config)
    except ClientError:
        logger.exception("Error connecting to SQS")
        raise
    else:
        return sqs


def is_queue_overloaded() -> bool:
    """Returns True if the queue length exceeds SQS_QUEUE_MAX_LENGTH.

    Uses ApproximateNumberOfMessages, which is eventually consistent.
    On any SQS error, fails open (returns False) so the caller can proceed.
    """
    sqs = get_sqs_client()
    try:
        queue_url = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)["QueueUrl"]
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        length = int(response["Attributes"]["ApproximateNumberOfMessages"])
        logger.debug(
            "SQS queue %s has %d messages (max: %d)", SQS_QUEUE_NAME, length, SQS_QUEUE_MAX_LENGTH
        )
    except ConnectTimeoutError, ReadTimeoutError, ClientError:
        logger.exception("Could not check queue length for %s, failing open", SQS_QUEUE_NAME)
        return False
    else:
        return length >= SQS_QUEUE_MAX_LENGTH


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
    except ConnectTimeoutError:
        logger.exception("Connection timeout sending message to SQS queue %s", SQS_QUEUE_NAME)
        raise
    except ReadTimeoutError:
        logger.exception("Read timeout sending message to SQS queue %s", SQS_QUEUE_NAME)
        raise
    except ClientError:
        logger.exception("Error sending message to SQS queue %s", SQS_QUEUE_NAME)
        raise
