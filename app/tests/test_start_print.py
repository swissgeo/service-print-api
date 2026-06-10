from unittest.mock import patch

from botocore.exceptions import ClientError

from pydantic import ValidationError

import pytest

from app.schemas.jobs import DBJobItem, PrintJobPayload
from app.settings import get_settings

API_PATH_PREFIX = get_settings().api_path_prefix

_PAYLOAD = {
    "print_format": "a4",
    "print_orientation": "landscape",
    "print_resolution": 96,
    "print_scale": 25000,
    "state": "cHJpbnRfbWFw",
}

_JOB_ID = "684394c1bef082925d690f05f75b3e248b6a56327229475985891fee84564d75"


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
        assert "reportPath" in data
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


class TestPrintJobPayload:
    def test_valid_full_payload(self):
        payload = PrintJobPayload(**_PAYLOAD)
        assert payload.print_format == "a4"
        assert payload.print_scale == 25000

    def test_print_scale_is_optional(self):
        payload = PrintJobPayload(
            print_format="a4",
            print_orientation="portrait",
            print_resolution=96,
            state="cHJpbnRfbWFw",
        )
        assert payload.print_scale is None

    @pytest.mark.parametrize("fmt", ["a0", "a1", "a2", "a3", "a4", "a5", "a6"])
    def test_all_valid_formats(self, fmt):
        payload = PrintJobPayload(**{**_PAYLOAD, "print_format": fmt})
        assert payload.print_format == fmt

    @pytest.mark.parametrize("orientation", ["portrait", "landscape"])
    def test_all_valid_orientations(self, orientation):
        payload = PrintJobPayload(**{**_PAYLOAD, "print_orientation": orientation})
        assert payload.print_orientation == orientation

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="print_format"):
            PrintJobPayload(**{**_PAYLOAD, "print_format": "b2"})

    def test_invalid_orientation_raises(self):
        with pytest.raises(ValidationError, match="print_orientation"):
            PrintJobPayload(**{**_PAYLOAD, "print_orientation": "diagonal"})

    def test_missing_required_field_raises(self):
        data = {k: v for k, v in _PAYLOAD.items() if k != "print_format"}
        with pytest.raises(ValidationError, match="print_format"):
            PrintJobPayload(**data)

    def test_wrong_type_for_resolution_raises(self):
        with pytest.raises(ValidationError, match="print_resolution"):
            PrintJobPayload(**{**_PAYLOAD, "print_resolution": "high"})

    @pytest.mark.parametrize("resolution", [72, 96, 150, 300])
    def test_valid_resolutions(self, resolution):
        payload = PrintJobPayload(**{**_PAYLOAD, "print_resolution": resolution})
        assert payload.print_resolution == resolution

    @pytest.mark.parametrize("resolution", [71, 301])
    def test_out_of_range_resolution_raises(self, resolution):
        with pytest.raises(ValidationError, match="print_resolution"):
            PrintJobPayload(**{**_PAYLOAD, "print_resolution": resolution})

    @pytest.mark.parametrize("scale", [1, 25000, 5_000_000])
    def test_valid_scales(self, scale):
        payload = PrintJobPayload(**{**_PAYLOAD, "print_scale": scale})
        assert payload.print_scale == scale

    @pytest.mark.parametrize("scale", [0, 5_000_001])
    def test_out_of_range_scale_raises(self, scale):
        with pytest.raises(ValidationError, match="print_scale"):
            PrintJobPayload(**{**_PAYLOAD, "print_scale": scale})
