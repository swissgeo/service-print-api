from __future__ import annotations

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

import pytest

from app.helpers.dynamo_db import get_print_job, insert_dynamodb


class TestGetPrintJob:
    @patch("app.helpers.dynamo_db.get_dynamodb_table")
    def test_returns_item_when_found(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
                "status": "open",
            }
        }
        mock_get_table.return_value = mock_table

        result = get_print_job("8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c")

        assert result == {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "open",
        }
        mock_table.get_item.assert_called_once_with(
            Key={"job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c"}
        )

    @patch("app.helpers.dynamo_db.get_dynamodb_table")
    def test_returns_none_when_not_found(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table

        result = get_print_job("nonexistent")

        assert result is None

    @patch("app.helpers.dynamo_db.get_dynamodb_table")
    def test_raises_client_error(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "GetItem"
        )
        mock_get_table.return_value = mock_table

        with pytest.raises(ClientError):
            get_print_job("8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c")


class TestInsertDynamodb:
    @patch("app.helpers.dynamo_db.get_dynamodb_table")
    def test_calls_put_item(self, mock_get_table):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "open",
        }

        insert_dynamodb(item)

        mock_table.put_item.assert_called_once_with(Item=item)

    @patch("app.helpers.dynamo_db.get_dynamodb_table")
    def test_raises_client_error(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "PutItem"
        )
        mock_get_table.return_value = mock_table

        with pytest.raises(ClientError):
            insert_dynamodb(
                {
                    "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
                    "status": "open",
                }
            )
