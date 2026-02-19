import hashlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.helpers.otel import strtobool
from app.helpers.utils import (
    build_job_response,
    dict_to_sha256_hash,
    get_hours_difference,
    get_iso_8601_timestamp,
    get_ttl_timestamp,
    is_domain_allowed,
    validate_payload,
)


class TestStrtobool:
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "y", "on"])
    def test_truthy_values(self, value):
        assert strtobool(value) is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "n", "off", ""])
    def test_falsy_values(self, value):
        assert strtobool(value) is False

    def test_whitespace_is_stripped(self):
        assert strtobool("  true  ") is True
        assert strtobool("  false  ") is False

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Cannot convert 'maybe' to boolean"):
            strtobool("maybe")


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


class TestGetIso8601Timestamp:
    def test_returns_utc_iso_string(self):
        result = get_iso_8601_timestamp()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0

    def test_returns_current_time(self):
        before = datetime.now(UTC)
        result = datetime.fromisoformat(get_iso_8601_timestamp())
        after = datetime.now(UTC)
        assert before <= result <= after

    @patch("app.helpers.utils.datetime")
    def test_uses_utc(self, mock_datetime):
        import datetime as dt  # noqa: PLC0415

        fixed = dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.UTC)
        mock_datetime.datetime.now.return_value = fixed
        mock_datetime.UTC = dt.UTC
        result = get_iso_8601_timestamp()
        assert result == "2024-01-15T12:00:00+00:00"


class TestGetTtlTimestamp:
    def test_returns_integer(self):
        result = get_ttl_timestamp()
        assert isinstance(result, int)

    def test_ttl_is_in_the_future(self):
        import time  # noqa: PLC0415

        now = int(time.time())
        result = get_ttl_timestamp()
        assert result > now

    @patch("app.helpers.utils.TTL_DYNAMODB_ITEM_HH", 48)
    @patch("app.helpers.utils.datetime")
    def test_ttl_matches_configured_hours(self, mock_datetime):
        import datetime as dt  # noqa: PLC0415

        fixed = dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.UTC)
        mock_datetime.datetime.now.return_value = fixed
        mock_datetime.UTC = dt.UTC
        mock_datetime.timedelta = dt.timedelta
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


class TestValidatePayload:
    def test_none_raises(self):
        with pytest.raises(ValueError, match="Payload must not be None"):
            validate_payload(None)

    def test_valid_payload(self):
        validate_payload({"key": "value"})

    def test_oversized_payload_raises(self):
        large = {"data": "x" * 200_000}
        with pytest.raises(ValueError, match="exceeds limit"):
            validate_payload(large)

    def test_empty_dict_is_valid(self):
        validate_payload({})


class TestIsDomainAllowed:
    @patch("app.helpers.utils.ALLOWED_DOMAINS_PATTERN", r"(example\.com|test\.org)")
    def test_allowed_domain(self):
        assert is_domain_allowed("https://example.com/path") is True

    @patch("app.helpers.utils.ALLOWED_DOMAINS_PATTERN", r"(example\.com)")
    def test_disallowed_domain(self):
        assert is_domain_allowed("https://evil.com/path") is False

    def test_no_hostname_returns_false(self):
        assert is_domain_allowed("not-a-url") is False

    @patch("app.helpers.utils.ALLOWED_DOMAINS_PATTERN", r"(.*)")
    def test_wildcard_allows_all(self):
        assert is_domain_allowed("https://anything.com") is True


class TestBuildJobResponse:
    def test_missing_optional_attributes_return_none(self):
        item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "open",
            "created_timestamp_iso_8601": "2023-10-27T10:00:00+00:00",
        }
        result = build_job_response(item)
        assert result == {
            "status": "open",
            "reportUrl": "/jobs/8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "created": "2023-10-27T10:00:00+00:00",
            "started": None,
            "finished": None,
            "pdfUrl": None,
            "message": None,
        }

    def test_present_optional_attributes_are_returned(self):
        item = {
            "job_id": "8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "status": "done",
            "created_timestamp_iso_8601": "2023-10-27T10:00:00+00:00",
            "started_timestamp_iso_8601": "2023-10-27T10:01:00+00:00",
            "finished_timestamp_iso_8601": "2023-10-27T10:05:00+00:00",
            "pdf_url": "https:/download.swissgeo.ch/8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c.pdf",  # noqa: E501
            "message": "Print completed",
        }
        result = build_job_response(item)
        assert result == {
            "status": "done",
            "reportUrl": "/jobs/8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c",
            "created": "2023-10-27T10:00:00+00:00",
            "started": "2023-10-27T10:01:00+00:00",
            "finished": "2023-10-27T10:05:00+00:00",
            "pdfUrl": "https:/download.swissgeo.ch/8683200e8facbf29ae87daae3ffb80c824cc88d277c4ee51fdbda4a96e1a5b9c.pdf",  # noqa: E501
            "message": "Print completed",
        }
