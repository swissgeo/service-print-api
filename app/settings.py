import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi import Depends
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.default"),
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )

    # API
    # root_path is the URL prefix the app is mounted under behind the ingress
    # (e.g. "/api/wps/v1/print"). FastAPI serves all routes AND the docs
    # (/docs, /redoc, /openapi.json) under it. Set via ROOT_PATH in deployment.
    root_path: str = ""
    # OpenAPI docs: when False, no spec/docs are served (public or internal)
    publish_openapi_spec: bool = False

    # CORS: comma-separated regex patterns, e.g. ".*" or "example\.com,localhost"
    allowed_domains: list[str] = [".*"]

    # Cache-Control headers
    cache_control: str = "no-store"
    cache_control_4xx: str = "public, max-age=120"

    # AWS
    aws_region: str = "eu-central-1"
    aws_local: bool = False
    moto_host: str = "localhost"
    moto_port: str = "5000"
    aws_connect_timeout: int = 5
    aws_read_timeout: int = 30

    # DynamoDB
    dynamodb_table_name: str = "service-print-jobs-local"

    # S3 — only used to build the PDF download URL in local dev. In prod the
    # ingress serves <root_path>/pdf/<job_id>.pdf directly from the bucket,
    # so these are not consulted. Must match the renderer's S3_BUCKET_NAME /
    # S3_PDF_PREFIX so the derived local URL points at the uploaded object.
    s3_bucket_name: str = "service-print-pdf-local"
    s3_pdf_prefix: str = "api/wps/v1/print/pdf"

    # SQS
    sqs_queue_name: str = "service-print-jobs-queue-local"
    sqs_queue_max_length: int = 100

    # Job behaviour
    expiration_time_hh_print_doc: int = 24
    ttl_dynamodb_item_hh: int = 48
    # Logging
    logging_enable_dev_server_logging: bool = False
    logging_config_file: Path | None = None
    logging_handlers_level: str | None = None

    # OTEL
    otel_sdk_disabled: bool = False
    otel_enable_fastapi: bool = False
    otel_enable_boto: bool = False
    otel_enable_otlp_exporter: bool = True
    otel_enable_metrics: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_otlp_insecure: bool = False
    otel_exporter_otlp_headers: str = ""

    @property
    def moto_endpoint(self) -> str:
        return f"http://{self.moto_host}:{self.moto_port}"

    @property
    def allowed_domains_pattern(self) -> str:
        return f"({'|'.join(self.allowed_domains)})"

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def parse_comma_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        return [item.strip() for item in v.split(",")]


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

if get_settings().aws_local:
    os.environ["AWS_ACCESS_KEY_ID"] = "123"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "123"  # noqa: S105
