import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

from app.settings import get_settings

logger = logging.getLogger(__name__)


def _botocore_config() -> Config:
    """Build a botocore Config with the configured connect/read timeouts."""
    settings = get_settings()
    return Config(
        connect_timeout=settings.aws_connect_timeout, read_timeout=settings.aws_read_timeout
    )


@asynccontextmanager
async def _sqs_client(session: aioboto3.Session) -> AsyncGenerator[Any]:
    settings = get_settings()
    endpoint_url = settings.moto_endpoint if settings.aws_local else None
    async with session.client(  # type: ignore[invalid-context-manager]
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=endpoint_url,
        config=_botocore_config(),
    ) as sqs:
        yield sqs


async def is_queue_overloaded(session: aioboto3.Session) -> bool:
    """Return True if the SQS approximate message count exceeds the configured maximum."""
    settings = get_settings()
    async with _sqs_client(session) as sqs:
        queue_url = (await sqs.get_queue_url(QueueName=settings.sqs_queue_name))["QueueUrl"]
        response = await sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        length = int(response["Attributes"]["ApproximateNumberOfMessages"])
        logger.debug(
            "SQS queue %s has %d messages (max: %d)",
            settings.sqs_queue_name,
            length,
            settings.sqs_queue_max_length,
        )
        return length > settings.sqs_queue_max_length


async def send_to_queue(message: dict[str, Any], session: aioboto3.Session) -> None:
    """Serialize message to JSON and send it to the configured SQS queue."""
    settings = get_settings()
    try:
        async with _sqs_client(session) as sqs:
            queue_url = (await sqs.get_queue_url(QueueName=settings.sqs_queue_name))["QueueUrl"]
            await sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
            )
            logger.info("Message sent to SQS queue %s", settings.sqs_queue_name)
    except ConnectTimeoutError:
        logger.exception(
            "Connection timeout sending message to SQS queue %s", settings.sqs_queue_name
        )
        raise
    except ReadTimeoutError:
        logger.exception("Read timeout sending message to SQS queue %s", settings.sqs_queue_name)
        raise
    except ClientError:
        logger.exception("Error sending message to SQS queue %s", settings.sqs_queue_name)
        raise
