from unittest.mock import patch

from botocore.exceptions import ClientError

import pytest

from app.config.settings import get_settings
from app.schemas.jobs import DBJobItem

API_PATH_PREFIX = get_settings().api_path_prefix

_PAYLOAD = {
    "format": "a4",
    "orientation": "landscape",
    "resolution": 96,
    "scale": 25000,
    "view": "print_map",
    "query": "key=value",
}

_JOB_ID = "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"


@pytest.fixture(autouse=True)
def mock_is_queue_overloaded():
    with patch("app.api.jobs.is_queue_overloaded", return_value=False):
        yield


class TestStartPrint:
    async def test_new_job_returns_202(self, client):
        with (
            patch("app.api.jobs.get_print_job", return_value=None),
            patch("app.api.jobs.insert_dynamodb") as mock_insert,
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "open"
        assert "reportUrl" in data
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    async def test_overloaded_queue_returns_503(self, client):
        with (
            patch("app.api.jobs.is_queue_overloaded", return_value=True),
            patch("app.api.jobs.get_print_job", return_value=None),
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 503

    async def test_invalid_payload_returns_400(self, client):
        response = await client.post(
            f"{API_PATH_PREFIX}/jobs",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "error" in response.json()

    async def test_existing_non_expired_job_returns_200(self, client):
        existing_item = DBJobItem.model_validate(
            {
                "job_id": _JOB_ID,
                "status": "open",
                "payload": _PAYLOAD,
                "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
            }
        )
        with (
            patch("app.api.jobs.get_print_job", return_value=existing_item),
            patch("app.api.jobs.get_hours_difference", return_value=1.0),
            patch("app.api.jobs.insert_dynamodb") as mock_insert,
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 200
        mock_insert.assert_not_called()
        mock_send.assert_not_called()

    async def test_expired_job_creates_new_job(self, client):
        existing_item = DBJobItem.model_validate(
            {
                "job_id": _JOB_ID,
                "status": "done",
                "payload": _PAYLOAD,
                "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
            }
        )
        with (
            patch("app.api.jobs.get_print_job", return_value=existing_item),
            patch("app.api.jobs.get_hours_difference", return_value=25.0),
            patch("app.api.jobs.insert_dynamodb") as mock_insert,
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    async def test_error_status_job_creates_new_job(self, client):
        existing_item = DBJobItem.model_validate(
            {
                "job_id": _JOB_ID,
                "status": "error",
                "payload": _PAYLOAD,
                "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
            }
        )
        with (
            patch("app.api.jobs.get_print_job", return_value=existing_item),
            patch("app.api.jobs.insert_dynamodb") as mock_insert,
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    async def test_dynamodb_insert_error_returns_500(self, client):
        with (
            patch("app.api.jobs.get_print_job", return_value=None),
            patch(
                "app.api.jobs.insert_dynamodb",
                side_effect=ClientError(
                    {"Error": {"Code": "500", "Message": "Internal"}}, "PutItem"
                ),
            ),
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 500
        assert "error" in response.json()
        mock_send.assert_not_called()

    async def test_sqs_error_returns_500(self, client):
        with (
            patch("app.api.jobs.get_print_job", return_value=None),
            patch("app.api.jobs.insert_dynamodb"),
            patch(
                "app.api.jobs.send_to_queue",
                side_effect=ClientError(
                    {"Error": {"Code": "500", "Message": "Internal"}}, "SendMessage"
                ),
            ),
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 500
        assert "error" in response.json()

    async def test_dynamodb_lookup_error_continues_gracefully(self, client):
        with (
            patch(
                "app.api.jobs.get_print_job",
                side_effect=ClientError(
                    {"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"
                ),
            ),
            patch("app.api.jobs.insert_dynamodb") as mock_insert,
            patch("app.api.jobs.send_to_queue") as mock_send,
        ):
            response = await client.post(f"{API_PATH_PREFIX}/jobs", json=_PAYLOAD)

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()
