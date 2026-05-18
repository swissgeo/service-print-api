from unittest.mock import AsyncMock, MagicMock

from botocore.exceptions import ClientError

import pytest

from app.helpers.dynamo_db import get_print_job, insert_dynamodb

_JOB_ID = "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"


def _dynamo_session(table_mock: AsyncMock) -> MagicMock:
    """Build a minimal aioboto3 session mock for DynamoDB resource usage."""
    dynamodb_resource = MagicMock()
    dynamodb_resource.Table = AsyncMock(return_value=table_mock)
    cm = AsyncMock()
    cm.__aenter__.return_value = dynamodb_resource
    session = MagicMock()
    session.resource.return_value = cm
    return session


_DYNAMO_ITEM = {
    "job_id": _JOB_ID,
    "status": "open",
    "payload": {},
    "created_timestamp_iso_8601": "2026-01-01T00:00:00+00:00",
}


class TestGetPrintJob:
    async def test_returns_item_when_found(self):
        mock_table = AsyncMock()
        mock_table.get_item.return_value = {"Item": _DYNAMO_ITEM}

        result = await get_print_job(_JOB_ID, session=_dynamo_session(mock_table))

        assert result is not None
        assert result.job_id == _JOB_ID
        assert result.status == "open"
        mock_table.get_item.assert_called_once_with(Key={"job_id": _JOB_ID})

    async def test_returns_none_when_not_found(self):
        mock_table = AsyncMock()
        mock_table.get_item.return_value = {}

        result = await get_print_job("nonexistent", session=_dynamo_session(mock_table))

        assert result is None

    async def test_raises_client_error(self):
        mock_table = AsyncMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"
        )

        with pytest.raises(ClientError):
            await get_print_job(_JOB_ID, session=_dynamo_session(mock_table))


class TestInsertDynamodb:
    async def test_calls_put_item(self):
        mock_table = AsyncMock()
        item = {"job_id": _JOB_ID, "status": "open"}

        await insert_dynamodb(item, session=_dynamo_session(mock_table))

        mock_table.put_item.assert_called_once_with(Item=item)

    async def test_raises_client_error(self):
        mock_table = AsyncMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "PutItem"
        )

        with pytest.raises(ClientError):
            await insert_dynamodb(
                {"job_id": _JOB_ID, "status": "open"}, session=_dynamo_session(mock_table)
            )
