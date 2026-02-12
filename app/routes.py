import logging
from http import HTTPStatus
from typing import Any

from botocore.exceptions import ClientError

from flask import Response, jsonify, make_response, request

from app.app import app
from app.config.settings import EXPIRATION_TIME_HH_PRINT_DOC
from app.config.version import APP_VERSION
from app.helpers.dynamo_db import get_dynamodb_table, insert_dynamodb, status_print
from app.helpers.functions import (
    get_hours_difference,
    get_iso_8601_timestamp,
    json_to_sha256_hash,
)

logger = logging.getLogger(__name__)

dynamodb_print_table = get_dynamodb_table()  # get the dynamodb table


@app.route("/jobs", methods=["POST"])
def start_print() -> tuple[dict[str, Any], HTTPStatus]:
    payload = request.get_json()
    job_id = json_to_sha256_hash(payload)

    # this error handling had to be done when the dynamodb has not entries yet
    # when job_id somehow does not exist jet (only appears on a brandnew table)
    try:
        print_queued = dynamodb_print_table.get_item(Key={"job_id": job_id})
    except ClientError:
        logger.exception("Error getting item from dynamodb")
        print_queued = {}

    # check, if exactly this print job already exist in the dynamodb
    if "Item" in print_queued:
        item = print_queued["Item"]
        # is the processing status of the document without error
        if item["status"] != "error" and item["created_timestamp_iso_8601"] != "":
            now = get_iso_8601_timestamp()
            # is the document older than EXPIRATION_TIME_HH hours
            if (
                get_hours_difference(now, str(item["created_timestamp_iso_8601"]))
                < EXPIRATION_TIME_HH_PRINT_DOC
            ):
                # if not return directly the info about the already on S3 stored document
                logger.info("Returning already registered print request")
                return status_print(job_id)
    # else, insert the payload to the dynamodb
    return insert_dynamodb(payload)


@app.route("/jobs/<job_id>", methods=["GET"])
def print_status(job_id: str) -> Response:
    if job_id is None:
        return make_response(
            jsonify({"error": "list of jobs is not implemented"}), HTTPStatus.NOT_FOUND
        )
    status_json, status_code = status_print(job_id)
    logger.warning(status_json)
    return make_response(jsonify(status_json), status_code)


@app.route("/checker", methods=["GET"])
def checker() -> Response:
    return make_response(
        jsonify({"success": True, "message": "OK", "version": APP_VERSION}), HTTPStatus.OK
    )


@app.route("/favicon.ico")
def favicon() -> Response | tuple[str, HTTPStatus]:
    return "", HTTPStatus.NO_CONTENT


@app.route("/robots.txt")
def robots() -> Response | tuple[str, HTTPStatus]:
    return "", HTTPStatus.NO_CONTENT
