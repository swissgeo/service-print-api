import json
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

import pytest

from app.config.settings import SQS_QUEUE_MAX_LENGTH
from app.helpers.sqs_queue import is_queue_overloaded, send_to_queue


class TestIsQueueOverloaded:
    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (SQS_QUEUE_MAX_LENGTH - 1, False),
            (SQS_QUEUE_MAX_LENGTH, False),
            (SQS_QUEUE_MAX_LENGTH + 1, True),
        ],
    )
    @patch("app.helpers.sqs_queue.get_sqs_client")
    def test_overloaded_boundary(self, mock_get_client, length, expected):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": str(length)}
        }
        mock_get_client.return_value = mock_sqs
        assert is_queue_overloaded() is expected


class TestSendToQueue:
    @patch("app.helpers.sqs_queue.get_sqs_client")
    def test_sends_message(self, mock_get_client):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        mock_get_client.return_value = mock_sqs
        message = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "open",
        }

        send_to_queue(message)

        mock_sqs.get_queue_url.assert_called_once()
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl="http://localhost/queue",
            MessageBody=json.dumps(message),
        )

    @patch("app.helpers.sqs_queue.get_sqs_client")
    def test_raises_client_error_on_get_queue_url(self, mock_get_client):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_url.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetQueueUrl"
        )
        mock_get_client.return_value = mock_sqs

        with pytest.raises(ClientError):
            send_to_queue(
                {"job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"}
            )

    @patch("app.helpers.sqs_queue.get_sqs_client")
    def test_raises_client_error_on_send_message(self, mock_get_client):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "http://localhost/queue"}
        mock_sqs.send_message.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "SendMessage"
        )
        mock_get_client.return_value = mock_sqs

        with pytest.raises(ClientError):
            send_to_queue(
                {"job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"}
            )
