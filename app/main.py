import logging
import logging.config
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any

import aioboto3
import yaml

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.jobs import router as jobs_router
from app.otel import initialize_instrumentation, shutdown_otel
from app.schemas.checker import CheckerResponse
from app.schemas.errors import ErrorDetail, ErrorResponse
from app.settings import get_settings
from app.version import __version__

logger = logging.getLogger(__name__)

settings = get_settings()

if settings.logging_enable_dev_server_logging:  # pragma: no cover
    if settings.logging_config_file:
        logging.config.dictConfig(yaml.safe_load(settings.logging_config_file.read_text()))
    else:
        logging.basicConfig(level=logging.INFO)

if settings.logging_handlers_level is not None:  # pragma: no cover
    for handler in logging.getLogger().handlers:
        handler.setLevel(settings.logging_handlers_level)


def _customize_openapi(app: FastAPI) -> None:
    """Remove the 422 responses FastAPI adds by default — they are replaced by 400."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema  # pragma: no cover
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        for method_item in app.openapi_schema.get("paths", {}).values():
            for param in method_item.values():
                param.get("responses", {}).pop("422", None)
        return app.openapi_schema

    app.openapi = custom_openapi  # ty:ignore[invalid-assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("Starting up service-print-api")

    app.state.session = aioboto3.Session()
    logger.info("aioboto3 session initialised")

    yield

    shutdown_otel()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Service Print API",
    summary="Accepts print job requests and queues them for processing",
    version=__version__,
    contact={"name": "swissgeo", "url": "https://www.swissgeo.ch/infos"},
    license_info={
        "name": "BSD 3-Clause License",
        "identifier": "BSD-3-Clause",
    },
    lifespan=lifespan,
)

# CORS — allow_origin_regex matches the full origin URL against the pattern.
# For local dev ALLOWED_DOMAINS=.* expands to (.*) which matches any origin.
# In production set ALLOWED_DOMAINS to hostname patterns, e.g. "example\.com,other\.ch".
app.add_middleware(
    CORSMiddleware,  # type: ignore[invalid-argument-type]
    allow_origin_regex=settings.allowed_domains_pattern,
    allow_methods=["GET", "HEAD", "OPTIONS", "POST"],
    allow_headers=["*"],
)

initialize_instrumentation(app)

app.include_router(jobs_router, prefix=settings.api_path_prefix)


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/robots.txt", include_in_schema=False)
async def _no_content() -> Response:
    return Response(status_code=HTTPStatus.NO_CONTENT)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error=ErrorDetail(code=400, message=str(exc))).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=exc.status_code, message=exc.detail)
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def handle_exception(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                code=HTTPStatus.INTERNAL_SERVER_ERROR,
                message="Internal server error, please consult logs",
            )
        ).model_dump(),
    )


_customize_openapi(app)


@app.get(
    f"{settings.api_path_prefix}/checker",
    response_model=CheckerResponse,
    tags=["Internal"],
    summary="Health check",
)
async def checker() -> CheckerResponse:
    return CheckerResponse(success=True, message="OK", version=__version__)
