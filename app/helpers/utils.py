from __future__ import annotations

import logging
import logging.config
import os
import re
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import yaml

from flask import Response, abort, jsonify, make_response, request

if TYPE_CHECKING:
    from flask import Flask
    from werkzeug.routing import Rule

from app.config.settings import ALLOWED_DOMAINS_PATTERN

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


def get_registered_method(app: Flask, url_rule: Rule | None) -> set[str]:
    """Returns the list of registered method for the given endpoint"""

    # The list of registered method is taken from the werkzeug.routing.Rule. A Rule object
    # has a methods property with the list of allowed method on an endpoint. If this property is
    # missing then all methods are allowed.
    # See https://werkzeug.palletsprojects.com/en/2.0.x/routing/#werkzeug.routing.Rule
    all_methods = ["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE"]
    return set(
        chain.from_iterable(
            [r.methods or all_methods for r in app.url_map.iter_rules() if r.rule == str(url_rule)]
        )
    )


def get_redirect_param(ignore_errors: bool = False) -> bool:
    try:
        redirect = strtobool(request.args.get("redirect", "true"))
    except ValueError as error:
        redirect = False
        if not ignore_errors:
            abort(400, f'Invalid "redirect" arg: {error}')
    return redirect


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
