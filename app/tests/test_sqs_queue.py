import json
from unittest.mock import AsyncMock, MagicMock

from botocore.exceptions import ClientError

import pytest

from app.config.settings import get_settings
from app.helpers.sqs_queue import is_queue_overloaded, send_to_queue

SQS_QUEUE_MAX_LENGTH = get_settings().sqs_queue_max_length

_JOB_ID = "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"


def _sqs_session(sqs_mock: AsyncMock) -> MagicMock:
    """Build a minimal aioboto3 session mock for SQS client usage."""
    cm = AsyncMock()
    cm.__aenter__.return_value = sqs_mock
    session = MagicMock()
    session.client.return_value = cm
    return session


class TestIsQueueOverloaded:
    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (SQS_QUEUE_MAX_LENGTH - 1, False),
            (SQS_QUEUE_MAX_LENGTH, False),
            (SQS_QUEUE_MAX_LENGTH + 1, True),
        ],
    )
    async def test_overloaded_boundary(self, length, expected):
        mock_sqs = AsyncMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": str(length)}
        }

        result = await is_queue_overloaded(session=_sqs_session(mock_sqs))

        assert result is expected


class TestSendToQueue:
    async def test_sends_message(self):
        mock_sqs = AsyncMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        message = {"job_id": _JOB_ID, "status": "open"}

        await send_to_queue(message, session=_sqs_session(mock_sqs))

        mock_sqs.get_queue_url.assert_called_once()
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl="http://localhost/queue",
            MessageBody=json.dumps(message),
        )

    async def test_raises_client_error_on_get_queue_url(self):
        mock_sqs = AsyncMock()
        mock_sqs.get_queue_url.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetQueueUrl"
        )

        with pytest.raises(ClientError):
            await send_to_queue({"job_id": _JOB_ID}, session=_sqs_session(mock_sqs))

    async def test_raises_client_error_on_send_message(self):
        mock_sqs = AsyncMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        mock_sqs.send_message.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "SendMessage"
        )

        with pytest.raises(ClientError):
            await send_to_queue({"job_id": _JOB_ID}, session=_sqs_session(mock_sqs))
