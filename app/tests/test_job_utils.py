import hashlib
from unittest.mock import patch

import pytest

from app.api.jobs import dict_to_sha256_hash, get_hours_difference, get_ttl_timestamp


class TestDictToSha256Hash:
    def test_returns_hex_string(self):
        result = dict_to_sha256_hash({"key": "value"})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_deterministic(self):
        data = {"a": 1, "b": 2}
        assert dict_to_sha256_hash(data) == dict_to_sha256_hash(data)

    def test_key_order_does_not_matter(self):
        hash1 = dict_to_sha256_hash({"b": 2, "a": 1})
        hash2 = dict_to_sha256_hash({"a": 1, "b": 2})
        assert hash1 == hash2

    def test_different_data_gives_different_hash(self):
        hash1 = dict_to_sha256_hash({"a": 1})
        hash2 = dict_to_sha256_hash({"a": 2})
        assert hash1 != hash2

    def test_matches_manual_computation(self):
        data = {"key": "value"}
        expected = "e43abcf3375244839c012f9633f95862d232a95b00d5bc7348b3098b9fed7f32"
        assert dict_to_sha256_hash(data) == expected

    def test_empty_dict(self):
        result = dict_to_sha256_hash({})
        expected = hashlib.sha256(b"{}").hexdigest()
        assert result == expected


class TestGetTtlTimestamp:
    def test_returns_integer(self):
        result = get_ttl_timestamp()
        assert isinstance(result, int)

    def test_ttl_is_in_the_future(self):
        import time  # noqa: PLC0415

        now = int(time.time())
        result = get_ttl_timestamp()
        assert result > now

    @patch("app.api.jobs.datetime")
    def test_ttl_matches_configured_hours(self, mock_datetime):
        import datetime as dt  # noqa: PLC0415

        fixed = dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.UTC)
        mock_datetime.now.return_value = fixed
        expected = fixed + dt.timedelta(hours=48)

        result = get_ttl_timestamp()

        assert result == int(expected.timestamp())


class TestGetHoursDifference:
    def test_one_hour(self):
        result = get_hours_difference(
            "2023-10-27T10:00:00+00:00",
            "2023-10-27T11:00:00+00:00",
        )
        assert result == 1.0

    def test_half_hour(self):
        result = get_hours_difference(
            "2023-10-27T10:00:00+00:00",
            "2023-10-27T10:30:00+00:00",
        )
        assert result == 0.5

    def test_24_hours(self):
        result = get_hours_difference(
            "2023-10-27T10:00:00+00:00",
            "2023-10-28T10:00:00+00:00",
        )
        assert result == 24.0

    def test_negative_difference(self):
        result = get_hours_difference(
            "2023-10-27T12:00:00+00:00",
            "2023-10-27T10:00:00+00:00",
        )
        assert result == -2.0

    def test_zero_difference(self):
        result = get_hours_difference(
            "2023-10-27T10:00:00+00:00",
            "2023-10-27T10:00:00+00:00",
        )
        assert result == 0.0

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            get_hours_difference("not-a-date", "2023-10-27T10:00:00+00:00")


