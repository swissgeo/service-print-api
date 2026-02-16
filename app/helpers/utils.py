from __future__ import annotations

import datetime
import hashlib
import json
import logging
import logging.config
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from flask import Response, jsonify, make_response

from app.config.settings import ALLOWED_DOMAINS_PATTERN, MAX_PAYLOAD_SIZE_BYTES

logger = logging.getLogger(__name__)

INVALID_BOOLEAN_ERROR = "Cannot convert '{value}' to boolean"


def strtobool(value: str) -> bool:
    value = value.lower().strip()
    if value in ("true", "1", "yes", "y", "on"):
        return True
    if value in ("false", "0", "no", "n", "off", ""):
        return False
    raise ValueError(INVALID_BOOLEAN_ERROR.format(value=value))


def get_logging_cfg() -> Any:
    cfg_file = os.getenv("LOGGING_CFG", "app/config/logging-cfg-local.yaml")
    if "LOGS_DIR" not in os.environ:
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        logs_dir = Path(__file__).resolve(strict=True).parent.parent.parent / "logs"
        os.environ["LOGS_DIR"] = str(logs_dir)
    print(f"LOGS_DIR is {os.environ['LOGS_DIR']}")  # noqa: T201
    print(f"LOGGING_CFG is {cfg_file}")  # noqa: T201

    with open(cfg_file, encoding="utf-8") as fd:
        config: Any = yaml.safe_load(os.path.expandvars(fd.read()))

    logger.debug("Load logging configuration from file %s", cfg_file)
    return config


def init_logging() -> None:
    config = get_logging_cfg()
    logging.config.dictConfig(config)


def make_error_msg(code: int | None, msg: str | None) -> Response:
    return make_response(
        jsonify({"success": False, "error": {"code": code, "message": msg}}),
        code,
    )


def is_domain_allowed(url: str) -> bool:
    """Check if the url contain a domain that is allowed"""
    domain = urlparse(url).hostname
    if domain:
        return re.fullmatch(ALLOWED_DOMAINS_PATTERN, domain) is not None
    return False


def dict_to_sha256_hash(data: dict[str, object]) -> str:
    """
    Converts a dictionary into a consistent SHA-256 hash.

    To ensure consistency (e.g., for dicts with different key orders but
    identical content), the function serializes the dict into a canonical
    JSON form (sorted keys, no whitespace) before hashing.

    Args:
        data: The input dictionary.

    Returns:
        A string representing the SHA-256 hash in hexadecimal format.
    """
    canonical_json_string = json.dumps(data, sort_keys=True, separators=(",", ":"))
    encoded_json = canonical_json_string.encode("utf-8")
    sha256_hash = hashlib.sha256(encoded_json)
    return sha256_hash.hexdigest()


def get_iso_8601_timestamp() -> str:
    """
    Generates the current UTC timestamp as a string in ISO 8601 format.

    The ISO 8601 format includes date, time, and timezone information,
    e.g., "YYYY-MM-DDTHH:MM:SS.ffffff+00:00" for UTC.

    Returns:
        A string representing the current UTC timestamp in ISO 8601 format.
    """
    # Get the current UTC time
    now_utc = datetime.datetime.now(datetime.UTC)

    # Format it into ISO 8601 string.
    # .isoformat() automatically handles the 'T' separator and timezone offset.
    # For UTC, it will append '+00:00'.
    return now_utc.isoformat()


def get_hours_difference(start_date_str: str, end_date_str: str) -> float:
    """
    Calculates the difference in hours between two ISO 8601 formatted date strings.

    Args:
        start_date_str: The starting date and time string in ISO 8601 format
        (e.g., '2023-10-27T10:00:00+00:00').
        end_date_str: The ending date and time string in ISO 8601 format
        (e.g., '2023-10-28T12:30:00+00:00').

    Returns:
        The difference in hours as a float.

    Raises:
        ValueError: If the date strings are not in valid ISO 8601 format.
    """
    try:
        # Parse the ISO 8601 strings into datetime objects.
        # .fromisoformat() handles various formats, including those with and without timezones.
        start_date = datetime.datetime.fromisoformat(start_date_str)
        end_date = datetime.datetime.fromisoformat(end_date_str)

        # Calculate the difference between the two datetime objects.
        # This results in a timedelta object.
        time_difference = end_date - start_date

        # Get the total number of seconds from the timedelta object.
        total_seconds = time_difference.total_seconds()

        # Convert the total seconds to hours and return the result.
        return total_seconds / 3600

    except ValueError as e:
        logger.exception("Invalid date format. Please use ISO 8601")
        raise ValueError("Invalid date format. Please use ISO 8601") from e


def validate_payload(payload: Any) -> None:
    """Validate the incoming request payload.

    Raises:
        ValueError: If the payload is None or exceeds MAX_PAYLOAD_SIZE_BYTES.
    """
    if payload is None:
        raise ValueError("Payload must not be None")
    payload_size = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    if payload_size > MAX_PAYLOAD_SIZE_BYTES:
        raise ValueError(
            f"Payload size {payload_size} bytes exceeds limit of {MAX_PAYLOAD_SIZE_BYTES} bytes"
        )


def build_job_response(item: dict[str, Any]) -> dict[str, Any]:
    """Build the standard job response dict from a DynamoDB item."""
    return {
        "status": item["status"],
        "reportUrl": f"/jobs/{item['job_id']}",
        "created": item["created_timestamp_iso_8601"],
        "started": item["started_timestamp_iso_8601"],
        "finished": item["finished_timestamp_iso_8601"],
    }
