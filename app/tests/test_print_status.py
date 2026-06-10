from unittest.mock import patch

from botocore.exceptions import ClientError

from app.schemas.jobs import DBJobItem
from app.settings import get_settings

API_PATH_PREFIX = get_settings().api_path_prefix

_JOB_ID = "e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"


class TestPrintStatus:
    async def test_job_found_returns_200(self, client):
        item = DBJobItem.model_validate(
            {
                "job_id": _JOB_ID,
                "status": "done",
                "payload": {},
                "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
                "started_timestamp_iso_8601": "2026-11-26T10:01:00+00:00",
                "finished_timestamp_iso_8601": "2026-11-26T10:05:00+00:00",
                "pdf_path": f"https://download.swissgeo.ch/{_JOB_ID}.pdf",
                "message": "Print completed",
            }
        )
        with patch("app.api.jobs.get_print_job", return_value=item):
            response = await client.get(f"{API_PATH_PREFIX}/jobs/{_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["reportPath"] == f"{API_PATH_PREFIX}/jobs/{_JOB_ID}"
        assert data["pdfPath"] == f"https://download.swissgeo.ch/{_JOB_ID}.pdf"
        assert data["message"] == "Print completed"

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
        assert data["pdfPath"] is None
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
