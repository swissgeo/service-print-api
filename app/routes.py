import logging
from http import HTTPStatus
from typing import Any

from botocore.exceptions import ClientError

from flask import Response, jsonify, make_response, request

from app.app import app
from app.config.settings import EXPIRATION_TIME_HH_PRINT_DOC
from app.config.version import APP_VERSION
from app.helpers.dynamo_db import get_dynamodb_table, get_print_job, insert_dynamodb
from app.helpers.sqs_queue import send_to_queue
from app.helpers.utils import (
    build_job_response,
    dict_to_sha256_hash,
    get_hours_difference,
    get_iso_8601_timestamp,
    validate_payload,
)

logger = logging.getLogger(__name__)


@app.route("/jobs", methods=["POST"])
def start_print() -> tuple[dict[str, Any], HTTPStatus]:
    payload = request.get_json()
    try:
        validate_payload(payload)
    except ValueError as e:
        return ({"error": str(e)}, HTTPStatus.BAD_REQUEST)
    job_id = dict_to_sha256_hash(payload)
    dynamodb_table = get_dynamodb_table()  # get the dynamodb table

    # this error handling had to be done when the dynamodb has not entries yet
    # when job_id somehow does not exist jet (only appears on a brandnew table)
    try:
        print_queued = dynamodb_table.get_item(Key={"job_id": job_id})
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
                get_hours_difference(str(item["created_timestamp_iso_8601"]), now)
                < EXPIRATION_TIME_HH_PRINT_DOC
            ):
                # if not return directly the info about the already on S3 stored document
                logger.info("Returning already registered print request")
                return (build_job_response(item), HTTPStatus.OK)
    # build the full item to insert into dynamodb and send to sqs
    item = {
        "job_id": job_id,
        "created_timestamp_iso_8601": get_iso_8601_timestamp(),
        "started_timestamp_iso_8601": "",
        "finished_timestamp_iso_8601": "",
        "payload": payload,
        "status": "open",
    }
    try:
        send_to_queue(item)
    except ClientError:
        logger.exception("Error sending item to SQS queue")
        return ({"error": "Error sending print job to queue"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        insert_dynamodb(item)
    except ClientError:
        logger.exception("Error inserting item into DynamoDB")
        return ({"error": "Error storing print job in database"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    return (build_job_response(item), HTTPStatus.ACCEPTED)


@app.route("/jobs", methods=["GET"])
def print_list() -> Response:
    return make_response(
        jsonify({"error": "Print job listing has not been implemented"}),
        HTTPStatus.NOT_IMPLEMENTED,
    )


@app.route("/jobs/<job_id>", methods=["GET"])
def print_status(job_id: str) -> Response:
    try:
        item = get_print_job(job_id)
    except ClientError:
        return make_response(
            jsonify({"error": "Error while looking for job_id"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    if item is None:
        return make_response(
            jsonify({"warning": f"No entry found for job id {job_id}"}),
            HTTPStatus.NOT_FOUND,
        )
    return make_response(jsonify(build_job_response(item)), HTTPStatus.OK)


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
