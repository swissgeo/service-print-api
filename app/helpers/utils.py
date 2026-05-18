import datetime
import hashlib
import json
import logging
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def dict_to_sha256_hash(data: dict[str, object]) -> str:
    """Serialize dict to canonical JSON (sorted keys, no whitespace) and return its SHA-256 hash."""
    canonical_json_string = json.dumps(data, sort_keys=True, separators=(",", ":"))
    encoded_json = canonical_json_string.encode("utf-8")
    sha256_hash = hashlib.sha256(encoded_json)
    return sha256_hash.hexdigest()


def get_ttl_timestamp() -> int:
    """Return a Unix epoch TTL timestamp offset by the configured number of hours from now."""
    now_utc = datetime.datetime.now(datetime.UTC)
    ttl = now_utc + datetime.timedelta(hours=get_settings().ttl_dynamodb_item_hh)
    return int(ttl.timestamp())


def get_hours_difference(start_date_str: str, end_date_str: str) -> float:
    """Return the difference in hours between two ISO 8601 datetime strings."""
    try:
        start_date = datetime.datetime.fromisoformat(start_date_str)
        end_date = datetime.datetime.fromisoformat(end_date_str)
        time_difference = end_date - start_date
        return time_difference.total_seconds() / 3600
    except ValueError as e:
        logger.exception("Invalid date format. Please use ISO 8601")
        raise ValueError("Invalid date format. Please use ISO 8601") from e


def validate_payload(payload: Any) -> None:
    """Raise ValueError if payload is None or its JSON size exceeds the configured limit."""
    if payload is None:
        raise ValueError("Payload must not be None")
    payload_size = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    max_size = get_settings().max_payload_size_bytes
    if payload_size > max_size:
        raise ValueError(f"Payload size {payload_size} bytes exceeds limit of {max_size} bytes")
