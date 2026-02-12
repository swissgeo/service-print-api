import logging
from http import HTTPStatus
from typing import Any

from botocore.exceptions import ClientError

from flask import Response, jsonify, make_response, request

from app.app import app
from app.config.settings import EXPIRATION_TIME_HH_PRINT_DOC
from app.config.version import APP_VERSION
from app.helpers.functions import (
    dict_to_http_response,
    get_dynamodb_table,
    get_hours_difference,
    get_iso_8601_timestamp,
    json_to_sha256_hash,
)

logger = logging.getLogger(__name__)

print_table = get_dynamodb_table()  # get the dynamodb table


@app.route("/jobs", methods=["POST"])
def start_print() -> dict[str, Any]:
    payload = request.get_json()
    job_id = json_to_sha256_hash(payload)

    # this error handling had to be done when the dynamodb has not entries yet
    # when job_id somehow does not exist jet (only appears on a brandnew table)
    try:
        print_queued = print_table.get_item(Key={"job_id": job_id})
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
    return insert_dynamodb(payload)


@app.route("/checker", methods=["GET"])
def checker() -> Response:
    return make_response(
        jsonify({"success": True, "message": "OK", "version": APP_VERSION}), HTTPStatus.OK
    )


@app.route("/favicon.ico")
def favicon() -> Response | tuple[str, HTTPStatus]:
    return "", HTTPStatus.NO_CONTENT  # No content


@app.route("/robots.txt")
def robots() -> Response | tuple[str, HTTPStatus]:
    return "", HTTPStatus.NO_CONTENT


def status_print(job_id: str | None) -> dict[str, Any]:
    try:
        print_queued = print_table.get_item(Key={"job_id": job_id})
        if "Item" in print_queued:
            item = print_queued["Item"]
            return dict_to_http_response(
                {
                    "status": item["status"],
                    "reportUrl": f"/jobs/{item['job_id']}",
                    "created": item["created_timestamp_iso_8601"],
                    "started": item["started_timestamp_iso_8601"],
                    "finished": item["finished_timestamp_iso_8601"],
                },
                HTTPStatus.OK,
            )
        return dict_to_http_response(
            {"warning": f"No entry found for job id {job_id}"}, HTTPStatus.NOT_FOUND
        )
    except ClientError:
        logger.exception("warning no print job found")
        return dict_to_http_response(
            {"error": "Error while looking for job_id"}, HTTPStatus.INTERNAL_SERVER_ERROR
        )


def insert_dynamodb(payload: dict[str, Any]) -> dict[str, Any]:
    # set values
    created_timestamp = get_iso_8601_timestamp()
    sha256_sum = json_to_sha256_hash(payload)
    status = "open"

    item_to_put = {
        "job_id": sha256_sum,
        "created_timestamp_iso_8601": created_timestamp,
        "started_timestamp_iso_8601": "",
        "finished_timestamp_iso_8601": "",
        "message": "",
        "payload": payload,
        "status": status,
    }

    # init dynamodb
    logger.info(item_to_put)
    try:
        logger.info("Put to dynamodb")
        put_response = print_table.put_item(Item=item_to_put)
        logger.info(put_response)
    except ClientError:
        logger.exception("Error updating dynamodb")
        return dict_to_http_response(
            {"error": "Error updating dynamodb"}, HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return dict_to_http_response(
        {
            "status": status,
            "reportUrl": f"/jobs/{sha256_sum}",
            "created": created_timestamp,
            "started": "",
            "finished": "",
        },
        HTTPStatus.ACCEPTED,
    )
