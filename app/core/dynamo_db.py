import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3

from app.core.aws import botocore_config
from app.schemas.jobs import DBJobItem
from app.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _dynamodb_resource(session: aioboto3.Session) -> AsyncGenerator[Any]:
    settings = get_settings()
    endpoint_url = settings.moto_endpoint if settings.aws_local else None
    async with session.resource(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=endpoint_url,
        config=botocore_config(),
    ) as dynamodb:
        yield dynamodb


async def insert_dynamodb(item: dict[str, Any], session: aioboto3.Session) -> None:
    """Insert a print job item into DynamoDB."""
    settings = get_settings()
    logger.info("Inserting job %s (status=%s)", item["job_id"], item["status"])
    async with _dynamodb_resource(session) as dynamodb:
        table = await dynamodb.Table(settings.dynamodb_table_name)
        await table.put_item(Item=item)
        logger.debug("Put job %s into DynamoDB (status=%s)", item["job_id"], item["status"])


async def get_print_job(job_id: str, session: aioboto3.Session) -> DBJobItem | None:
    """Retrieve a print job from DynamoDB by job_id, or None if not found."""
    settings = get_settings()
    async with _dynamodb_resource(session) as dynamodb:
        table = await dynamodb.Table(settings.dynamodb_table_name)
        response = await table.get_item(Key={"job_id": job_id})
    if "Item" in response:
        return DBJobItem.model_validate(dict(response["Item"]))
    return None
