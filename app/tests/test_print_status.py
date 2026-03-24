from unittest.mock import patch

from botocore.exceptions import ClientError

from app.config.settings import API_PATH_PREFIX


class TestPrintStatus:
    @patch("app.routes.get_print_job")
    def test_job_found_returns_200(self, mock_get_job, client):
        mock_get_job.return_value = {
            "job_id": "e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633",
            "status": "finished",
            "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
            "started_timestamp_iso_8601": "2026-11-26T10:01:00+00:00",
            "finished_timestamp_iso_8601": "2026-1-26T10:05:00+00:00",
            "pdf_url": "https://download.swissgeo.ch/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633.pdf",
            "message": "Print completed",
        }

        response = client.get(
            f"{API_PATH_PREFIX}/jobs/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "finished"
        assert (
            data["reportUrl"]
            == f"http://localhost{API_PATH_PREFIX}/jobs/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"
        )
        assert (
            data["pdfUrl"]
            == "https://download.swissgeo.ch/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633.pdf"
        )
        assert data["message"] == "Print completed"

    @patch("app.routes.get_print_job")
    def test_job_found_with_missing_optional_attrs(self, mock_get_job, client):
        mock_get_job.return_value = {
            "job_id": "e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633",
            "status": "open",
            "created_timestamp_iso_8601": "2026-10-27T10:00:00+00:00",
        }

        response = client.get(
            f"{API_PATH_PREFIX}/jobs/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["started"] is None
        assert data["finished"] is None
        assert data["pdfUrl"] is None
        assert data["message"] is None

    @patch("app.routes.get_print_job")
    def test_job_not_found_returns_404(self, mock_get_job, client):
        mock_get_job.return_value = None

        response = client.get(f"{API_PATH_PREFIX}/jobs/nonexistent")

        assert response.status_code == 404
        assert "warning" in response.get_json()

    @patch("app.routes.get_print_job")
    def test_dynamodb_error_returns_500(self, mock_get_job, client):
        mock_get_job.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"
        )

        response = client.get(
            f"{API_PATH_PREFIX}/jobs/e3cb0a487ff4cfafe59eaca4ec13d066f30f5e4b70b8dc978ba5e25636865633"
        )

        assert response.status_code == 500
        assert "error" in response.get_json()


class TestPrintList:
    def test_returns_501(self, client):
        response = client.get(f"{API_PATH_PREFIX}/jobs")

        assert response.status_code == 501
        assert "error" in response.get_json()
