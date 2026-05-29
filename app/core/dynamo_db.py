import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

from app.schemas.jobs import DBJobItem
from app.settings import get_settings

logger = logging.getLogger(__name__)


def _botocore_config() -> Config:
    """Build a botocore Config with the configured connect/read timeouts."""
    settings = get_settings()
    return Config(
        connect_timeout=settings.aws_connect_timeout, read_timeout=settings.aws_read_timeout
    )


@asynccontextmanager
async def _dynamodb_resource(session: aioboto3.Session) -> AsyncGenerator[Any]:
    settings = get_settings()
    endpoint_url = settings.moto_endpoint if settings.aws_local else None
    async with session.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=endpoint_url,
        config=_botocore_config(),
    ) as dynamodb:
        yield dynamodb


async def insert_dynamodb(item: dict[str, Any], session: aioboto3.Session) -> None:
    """Insert a print job item into DynamoDB."""
    settings = get_settings()
    logger.info(item)
    try:
        async with _dynamodb_resource(session) as dynamodb:
            table = await dynamodb.Table(settings.dynamodb_table_name)
            await table.put_item(Item=item)
            logger.debug("Put job %s into DynamoDB (status=%s)", item["job_id"], item["status"])
    except ConnectTimeoutError:
        logger.exception("Connection timeout inserting job %s into DynamoDB", item["job_id"])
        raise
    except ReadTimeoutError:
        logger.exception("Read timeout inserting job %s into DynamoDB", item["job_id"])
        raise
    except ClientError:
        logger.exception("Error updating dynamodb")
        raise


async def get_print_job(job_id: str | None, session: aioboto3.Session) -> DBJobItem | None:
    """Retrieve a print job from DynamoDB by job_id, or None if not found."""
    settings = get_settings()
    try:
        async with _dynamodb_resource(session) as dynamodb:
            table = await dynamodb.Table(settings.dynamodb_table_name)
            response = await table.get_item(Key={"job_id": job_id})
    except ConnectTimeoutError:
        logger.exception("Connection timeout looking up print job %s", job_id)
        raise
    except ReadTimeoutError:
        logger.exception("Read timeout looking up print job %s", job_id)
        raise
    except ClientError:
        logger.exception("Error looking up print job %s", job_id)
        raise
    if "Item" in response:
        return DBJobItem.model_validate(dict(response["Item"]))
    return None
