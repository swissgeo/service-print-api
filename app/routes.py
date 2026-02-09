import logging

from flask import Response, jsonify, make_response

from app.app import app
from app.config.version import APP_VERSION

logger = logging.getLogger(__name__)


@app.route("/checker", methods=["GET"])
def checker() -> Response:
    return make_response(jsonify({"success": True, "message": "OK", "version": APP_VERSION}), 200)


@app.route("/favicon.ico")
def favicon() -> Response | tuple[str, int]:
    return "", 204  # No content


@app.route("/robots.txt")
def robots() -> Response | tuple[str, int]:
    return "", 204
