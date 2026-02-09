import logging
import time

from flask import Flask, Response, abort, g, request
from werkzeug.exceptions import HTTPException

from app.config.settings import CACHE_CONTROL, CACHE_CONTROL_4XX, STAGING
from app.helpers.utils import (
    get_redirect_param,
    get_registered_method,
    is_domain_allowed,
    make_error_msg,
)

logger = logging.getLogger(__name__)

# Standard Flask application initialization

app = Flask(__name__)
app.config.from_mapping({"TRAP_HTTP_EXCEPTIONS": True})

HTTP_BAD_REQUEST_CODE = 400


@app.before_request
# Add quick log of the routes used to all request.
# Important: this should be the first before_request method, to ensure
# a failure in another pre request method would stop logging.
def log_route() -> None:
    g.setdefault("request_started", time.time())
    logger.debug("%s %s", request.method, request.path)


# Reject request from non allowed origins
# TODO Do not know if STAGING == local is the right approach
@app.before_request
def validate_origin() -> None:
    if (request.endpoint == "get_shortlink" and get_redirect_param()) or STAGING == "local":
        # Don't validate the origin for the get_shortlink endpoint with redirect.
        # The main purpose of this endpoint is to share a link, so this link may be used by
        # any origin (anyone)
        return

    # The Origin headers is automatically set by the browser and cannot be changed by the javascript
    # application. Unfortunately this header is only set if the request comes from another origin.
    # Sec-Fetch-Site header is set to `same-origin` by most of the browser except by Safari !
    # The best protection would be to use the Sec-Fetch-Site and Origin header, however this is
    # not supported by Safari. Therefore we added a fallback to the Referer header for Safari.
    sec_fetch_site = request.headers.get("Sec-Fetch-Site", None)
    origin = request.headers.get("Origin", None)
    referrer = request.headers.get("Referer", None)

    if origin is not None:
        if is_domain_allowed(origin):
            return
        logger.error("Origin=%s is not allowed", origin)
        abort(403, "Permission denied")

    if sec_fetch_site is not None:
        if sec_fetch_site in ["same-origin", "same-site"]:
            return
        logger.error("Sec-Fetch-Site=%s is not allowed", sec_fetch_site)
        abort(403, "Permission denied")

    if referrer is not None:
        if is_domain_allowed(referrer):
            return
        logger.error("Referer=%s is not allowed", referrer)
        abort(403, "Permission denied")

    logger.error("Referer and/or Origin and/or Sec-Fetch-Site headers not set")
    abort(403, "Permission denied")


@app.after_request
def add_charset(response: Response) -> Response:
    # Python uses UTF-8 as charset by default
    if response.headers.get("Content-Type") == "application/json":
        response.headers.set("Content-Type", "application/json; charset=utf-8")
    return response


# Add CORS Headers to all request
@app.after_request
def add_generic_cors_header(response: Response) -> Response:
    # Do not add CORS header to internal /checker endpoint.
    if request.endpoint == "checker":
        return response

    if request.endpoint == "get_shortlink" and get_redirect_param(ignore_errors=True):
        # redirect endpoint are allowed from all origins
        response.headers["Access-Control-Allow-Origin"] = "*"
    else:
        response.headers["Access-Control-Allow-Origin"] = request.host_url
        if "Origin" in request.headers and is_domain_allowed(request.headers["Origin"]):
            response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
    response.headers["Vary"] = "Origin"

    # Always add the allowed methods.
    response.headers.set(
        "Access-Control-Allow-Methods", ", ".join(get_registered_method(app, request.url_rule))
    )
    response.headers.set("Access-Control-Allow-Headers", "*")
    return response


@app.after_request
def add_cache_control_header(response: Response) -> Response:
    # For /checker route we let the frontend proxy decide how to cache it.
    if request.method == "GET" and request.endpoint != "checker":
        if response.status_code >= HTTP_BAD_REQUEST_CODE:
            response.headers.set("Cache-Control", CACHE_CONTROL_4XX)
        else:
            response.headers.set("Cache-Control", CACHE_CONTROL)
    return response


@app.after_request
def log_response(response: Response) -> Response:
    logger.info(
        "%s %s - %s",
        request.method,
        request.path,
        response.status,
        extra={
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers.items()),
                "json": response.json,
            },
            "duration": time.time() - g.get("request_started", time.time()),
        },
    )
    return response


# Register error handler to make sure that every error returns a json answer
@app.errorhandler(Exception)
def handle_exception(err: Exception) -> Response:
    """Return JSON instead of HTML for HTTP errors."""
    if isinstance(err, HTTPException):
        logger.error(err)
        return make_error_msg(err.code, err.description)

    logger.exception("Unexpected exception: %s", err)
    return make_error_msg(500, "Internal server error, please consult logs")
