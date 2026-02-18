from __future__ import annotations

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


class TestStartPrint:
    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    def test_new_job_returns_202(self, mock_get_table, mock_insert, mock_send, client):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data["status"] == "open"
        assert "reportUrl" in data
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    def test_invalid_payload_returns_400(self, client):
        response = client.post("/jobs", content_type="application/json", data="null")

        assert response.status_code == 400
        assert "error" in response.get_json()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    @patch("app.routes.get_hours_difference", return_value=1.0)
    def test_existing_non_expired_job_returns_200(
        self,
        mock_hours,  # noqa: ARG002
        mock_get_table,
        mock_insert,
        mock_send,
        client,
    ):
        existing_item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "open",
            "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
        }
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": existing_item}
        mock_get_table.return_value = mock_table

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 200
        mock_insert.assert_not_called()
        mock_send.assert_not_called()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    @patch("app.routes.get_hours_difference", return_value=25.0)
    def test_expired_job_creates_new_job(
        self,
        mock_hours,  # noqa: ARG002
        mock_get_table,
        mock_insert,
        mock_send,
        client,
    ):
        existing_item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "done",
            "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
        }
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": existing_item}
        mock_get_table.return_value = mock_table

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    def test_error_status_job_creates_new_job(self, mock_get_table, mock_insert, mock_send, client):
        existing_item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "error",
            "created_timestamp_iso_8601": "2026-11-26T10:00:00+00:00",
        }
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": existing_item}
        mock_get_table.return_value = mock_table

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    def test_dynamodb_insert_error_returns_500(
        self, mock_get_table, mock_insert, mock_send, client
    ):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        mock_insert.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "PutItem"
        )

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 500
        assert "error" in response.get_json()
        mock_send.assert_not_called()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    def test_sqs_error_returns_500(self, mock_get_table, mock_insert, mock_send, client):  # noqa: ARG002
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        mock_send.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "SendMessage"
        )

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 500
        assert "error" in response.get_json()

    @patch("app.routes.send_to_queue")
    @patch("app.routes.insert_dynamodb")
    @patch("app.routes.get_dynamodb_table")
    def test_dynamodb_lookup_error_continues_gracefully(
        self, mock_get_table, mock_insert, mock_send, client
    ):
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"
        )
        mock_get_table.return_value = mock_table

        response = client.post(
            "/jobs",
            json={
                "format": "a4",
                "orientation": "landscape",
                "resolution": 96,
                "scale": 25000,
                "view": "print_map",
                "query": "key=value",
            },
        )

        assert response.status_code == 202
        mock_insert.assert_called_once()
        mock_send.assert_called_once()
