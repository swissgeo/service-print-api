import datetime
import hashlib
import json
import logging
import re
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_dynamodb.service_resource import Table

from app.config.settings import AWS_DEFAULT_REGION, AWS_DYNAMODB_PORT, AWS_LOCAL, DYNAMODB_TABLE

logger = logging.getLogger(__name__)


def json_to_sha256_hash(json_object: dict[str, object]) -> str:
    """
    Converts a JSON object into a consistent SHA-256 hash.

    To ensure consistency (e.g., for JSON strings with different key orders
    or whitespace but identical content), the function first parses the
    JSON string and then re-serializes it into a canonical form
    (sorted keys, no indentation) before hashing.

    Args:
        json_string: The input JSON string.

    Returns:
        A string representing the SHA-256 hash in hexadecimal format.
    """
    try:
        # Re-serialize the object into a canonical JSON string.
        # - sort_keys=True ensures consistent key order.
        # - separators=(',', ':') removes all whitespace between items and keys/values.
        # This step is crucial for consistent hashing of semantically identical JSON.
        canonical_json_string = json.dumps(json_object, sort_keys=True, separators=(",", ":"))

    except json.JSONDecodeError as e:
        logger.exception("Invalid JSON string provided")
        raise ValueError("Invalid JSON string provided") from e

    # Encode the canonical JSON string to bytes (SHA-256 works on bytes)
    encoded_json = canonical_json_string.encode("utf-8")

    # Calculate the SHA-256 hash
    sha256_hash = hashlib.sha256(encoded_json)

    # Return the hexadecimal representation of the hash
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
        The difference in hours as a float. Returns 0.0 and prints an error
        if the date strings are not in the correct format.
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


def dict_to_http_response(
    data: dict[str, Any], http_status_code: HTTPStatus = HTTPStatus.OK
) -> dict[str, Any]:
    """
    Converts a Python dictionary to a JSON string.

    Args:
        data: The dictionary to be converted. The keys are expected to be strings,
              and values can be of any JSON-serializable type (e.g., str, int, float,
              bool, None, list, or other dicts).

    Returns:
        A JSON formatted string representation of the dictionary.

    Raises:
        TypeError: If the dictionary or any of its nested values are not JSON serializable.
    """
    if http_status_code == HTTPStatus.OK:
        logger.info(data)
    else:
        logger.warning(data)

    try:
        return {
            "statusCode": http_status_code,
            "body": json.dumps(data),
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        }
    except TypeError as e:
        logger.exception("dictionary contains non-JSON serializable data")
        raise TypeError("dictionary contains non-JSON serializable data") from e


def get_dynamodb() -> DynamoDBServiceResource:
    """
    Initializes and returns a DynamoDB ServiceResource object.

    This function dynamically connects to either a local DynamoDB instance
    (for development with AWS SAM) or to the AWS cloud-based service.
    This behavior is controlled by the 'AWS_LOCAL' flag.

    Returns:
        DynamoDBServiceResource: A high-level boto3 ServiceResource object for DynamoDB.

    Raises:
        ClientError: If there is an issue connecting to the DynamoDB endpoint,
                     such as network problems or invalid credentials.
    """
    # init dynamodb
    try:
        # condition if working locally for development or not
        if AWS_LOCAL:
            logger.info("Connecting to locally running dynamodb")
            dynamodb = cast(
                "DynamoDBServiceResource",
                boto3.resource(
                    "dynamodb",
                    endpoint_url=f"http://localhost:{AWS_DYNAMODB_PORT}",
                    region_name=AWS_DEFAULT_REGION,
                ),
            )
        else:
            logger.info("Connecting to dynamodb on aws")
            dynamodb = cast("DynamoDBServiceResource", boto3.resource("dynamodb"))
    except ClientError:
        logger.exception("Error connecting dynamodb")
        raise
    else:
        return dynamodb


def get_dynamodb_table() -> Table:
    """
    Returns a high-level DynamoDB Table resource object for the specified table.

    This function acts as a factory, creating a boto3 Table resource object
    which provides a high-level, object-oriented interface for interacting
    with a specific DynamoDB table.

    Returns:
        DynamoDBTableResource: The boto3 Table resource object for the table
                               defined by DYNAMODB_TABLE.
    """
    dynamodb: DynamoDBServiceResource = get_dynamodb()
    return dynamodb.Table(DYNAMODB_TABLE)  # ty: ignore[unresolved-attribute]


def get_job_id_from_path(path: str) -> str | None:
    """
    Extracts a job ID from a given path string using a regular expression.

    This function is designed to parse paths from an AWS Lambda Function URL or
    an API Gateway HTTP API, where path parameters are not automatically
    extracted. It looks for a path in the format "/jobs/{job_id}".

    Args:
        path: The path string to parse, e.g., "/jobs/123-abc-456".

    Returns:
        The extracted job ID as a string, or None if the path does not match
        the expected pattern.
    """
    job_id = None
    # Define the regex pattern to match the path
    # The '(.*?)' is a capture group for the path parameter
    path_pattern = re.compile(r"^/jobs/(?P<job_id>[^/]+)$")

    # Try to match the path against the pattern
    match = path_pattern.match(path)

    if match:
        # If a match is found, extract the named capture groups
        path_parameters = match.groupdict()
        job_id = str(path_parameters.get("job_id"))
    return job_id
