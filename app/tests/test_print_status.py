from typing import Any
from unittest.mock import patch

from botocore.exceptions import ClientError

from app.schemas.jobs import DBJobItem
from app.settings import Settings, get_settings

_settings = get_settings()
API_PATH_PREFIX = _settings.api_path_prefix
# Matches the test client's base_url (see conftest.py), used by request.base_url.
API_BASE_URL = "http://test"

_JOB_ID = "e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"


def _settings_with(**overrides: Any) -> Settings:
    """A settings copy with overrides, for pinning aws_local in pdfUrl tests."""
    return get_settings().model_copy(update=overrides)


def _finished_item() -> DBJobItem:
    return DBJobItem.model_validate(
        {
            "job_id": _JOB_ID,
            "status": "finished",
            "payload": {},
            "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
            "started_timestamp_iso_8601": "2026-11-26T10:01:00+00:00",
            "finished_timestamp_iso_8601": "2026-11-26T10:05:00+00:00",
            "message": "Print completed",
        }
    )


class TestPrintStatus:
    async def test_job_found_returns_200(self, client):
        item = _finished_item()
        with (
            patch("app.api.jobs.get_print_job", return_value=item),
            patch("app.api.jobs.get_settings", return_value=_settings_with(aws_local=False)),
        ):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/{_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "finished"
        assert data["reportUrl"] == f"{API_BASE_URL}{API_PATH_PREFIX}/jobs/{_JOB_ID}"
        # In prod the pdfUrl is the api-origin path served from the bucket by the proxy.
        assert data["pdfUrl"] == f"{API_BASE_URL}{API_PATH_PREFIX}/pdf/{_JOB_ID}.pdf"
        assert data["message"] == "Print completed"

    async def test_job_found_local_mode_points_at_moto(self, client):
        settings = _settings_with(aws_local=True)
        with (
            patch("app.api.jobs.get_print_job", return_value=_finished_item()),
            patch("app.api.jobs.get_settings", return_value=settings),
        ):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/{_JOB_ID}")

        expected = (
            f"{settings.moto_endpoint}/{settings.s3_bucket_name}"
            f"/{settings.s3_pdf_prefix}/{_JOB_ID}.pdf"
        )
        assert response.json()["pdfUrl"] == expected

    async def test_job_found_with_missing_optional_attrs(self, client):
        item = DBJobItem.model_validate(
            {
                "job_id": _JOB_ID,
                "status": "open",
                "payload": {},
                "created_timestamp_iso_8601": "2026-10-27T10:00:00+00:00",
            }
        )
        with patch("app.api.jobs.get_print_job", return_value=item):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/{_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["started"] is None
        assert data["finished"] is None
        assert data["pdfUrl"] is None
        assert data["message"] is None

    async def test_job_not_found_returns_404(self, client):
        with patch("app.api.jobs.get_print_job", return_value=None):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/nonexistent")

        assert response.status_code == 404
        assert "error" in response.json()

    async def test_dynamodb_error_returns_500(self, client):
        with patch(
            "app.api.jobs.get_print_job",
            side_effect=ClientError({"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"),
        ):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/{_JOB_ID}")

        assert response.status_code == 500
        assert "error" in response.json()


class TestPrintList:
    async def test_returns_501(self, client):
        response = await client.get(f"{API_PATH_PREFIX}/jobs")

        assert response.status_code == 501
        assert "error" in response.json()
