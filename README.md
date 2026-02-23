# service-print-api

| Branch | Status |
|--------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiNXRGbGtlM2FoVXVNTElKVmRybVB4QTdab2dzUi9sUzN5ZGJ2eU1XeVY3Qjc0bFRJbDhVWkZPK2M1ZVZpQ3RZMDdRbDNBM2tMZmJXUG5VcjF4QnBJdmo4PSIsIml2UGFyYW1ldGVyU3BlYyI6IlNTbndCOTdHVDVxaEQ0MlAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiNXRGbGtlM2FoVXVNTElKVmRybVB4QTdab2dzUi9sUzN5ZGJ2eU1XeVY3Qjc0bFRJbDhVWkZPK2M1ZVZpQ3RZMDdRbDNBM2tMZmJXUG5VcjF4QnBJdmo4PSIsIml2UGFyYW1ldGVyU3BlYyI6IlNTbndCOTdHVDVxaEQ0MlAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) |

## Table of Content

- [Table of Content](#table-of-content)
- [Summary Of The Project](#summary-of-the-project)
- [Service API](#service-api)
- [Versioning](#versioning)
- [Local Development](#local-development)
  - [Dependencies](#dependencies)
  - [Setup](#setup)
  - [Updating Packages](#updating-packages)
- [Deployment configuration](#deployment-configuration)
  - [OpenTelemetry (tracing)](#opentelemetry-tracing)
    - [Local tracing setup](#local-tracing-setup)



## Summary Of The Project

`service-print-api` is as service that has been built to be communicating with a client, from whom its receiving print commands and putting them into a queue to be processed. Most probably this client is the new webmapviewer of swissgeo.

After a client has POSTed (HTTP POST) a print command `service-print-api` returns an answer with an ID of this specific print command. With this ID the client can ask (via HTTP GET) the `service-print-api` about the status of the print.

As soon as the print has been accomplished, the client recives a positive status with a link to download the created pdf document.

## Service API

[Here the REST API specification](https://swissgeoplatform.atlassian.net/wiki/spaces/PB/pages/105218145/Communication), which has been implemented as described.

Furthermore there exists the checker GET endpoint to test, if the server is up:

| Path | Method | Argument | Response Type |
|------|--------|----------|---------------|
| /checker | GET | - | application/json |
| /jobs | POST | json (f.ex. post_print.sh) | application/json |
| /jobs/<job_id> | GET | job_id | application/json |

## Versioning

This service uses [SemVer](https://semver.org/) as versioning scheme. The versioning is automatically handled by `.github/workflows/main.yml` file.

See also [Git Flow - Versioning](https://github.com/geoadmin/doc-guidelines/blob/master/GIT_FLOW.md#versioning) for more information on the versioning guidelines.

## Local Development

### Dependencies

Prequisits on host for development and build:

- python version 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- `docker` and `docker compose`

### Setup

To create and activate a virtual Python environment with all dependencies installed:

```bash
make setup
```

To start the local aws stack for development (dynamodb and sqs):

```bash
make start-localstack
```

### Updating Packages

All packages used in production are pinned to a major version. Automatically updating these packages
will use the latest minor (or patch) version available. Packages used for development, on the other
hand, are not pinned unless they need to be used with a specific version of a production package
(for example, boto3-stubs for boto3).

To update the packages to the latest minor/compatible versions, run:

```bash
uv sync --upgrade
```

To see what major/incompatible releases would be available, run:

```bash
uv pip list --outdated
```

To update packages to a new major release, run:

```bash
uv add Flask~=3.1
```

## Deployment configuration

The service is configured by Environment Variable:

| Env         | Default               | Description                            |
|-------------|-----------------------|----------------------------------------|
| HTTP_PORT | `3000` | Port the HTTP server listens on |
| AWS_LOCAL | `false` | Set to `true` to point AWS clients at LocalStack instead of real AWS |
| LOCALSTACK_ENDPOINT | `http://localhost:4566` | Endpoint URL of the LocalStack instance used in local development |
| ALLOWED_DOMAINS | `.*` | Comma-separated list of regex patterns for CORS allowed origins |
| CACHE_CONTROL | `public, max-age=31536000` | `Cache-Control` header value for successful responses |
| CACHE_CONTROL_4XX | `public, max-age=3600` | `Cache-Control` header value for 4xx error responses |
| DYNAMODB_TABLE_NAME | `service-print-jobs-local` | The name of the DynamoDB table storing print job info |
| SQS_QUEUE_NAME | `service-print-jobs-queue-local` | The name of the SQS queue |
| EXPIRATION_TIME_HH_PRINT_DOC | `24` | Expiration time in hours before re-generating an already existing PDF |
| TTL_DYNAMODB_ITEM_HH | `48` | Time-to-live in hours for DynamoDB items |
| MAX_PAYLOAD_SIZE_BYTES | `102400` | Maximum allowed request payload size in bytes (default: 100 KB) |
| AWS_CONNECT_TIMEOUT | `5` | Timeout in seconds for establishing a connection to DynamoDB/SQS |
| AWS_READ_TIMEOUT | `30` | Timeout in seconds for reading a response from DynamoDB/SQS |

### OpenTelemetry (tracing)

| Env | Default | Description |
| --- | ------- | ----------- |
| OTEL_SDK_DISABLED | `false` | Set to `true` to disable all OTEL instrumentation |
| OTEL_ENABLE_FLASK | `false` | Set to `true` to enable automatic tracing of Flask HTTP requests |
| OTEL_ENABLE_LOGGING | `false` | Set to `true` to inject `otelTraceID` and `otelSpanID` into log records |
| OTEL_ENABLE_BOTOCORE | `false` | Set to `true` to enable tracing of DynamoDB and SQS calls |
| OTEL_EXPORTER_OTLP_ENDPOINT | `http://localhost:4317` | OTLP gRPC endpoint of the collector |
| OTEL_EXPORTER_OTLP_INSECURE | `false` | Set to `true` to use an insecure (non-TLS) connection to the collector |
| OTEL_EXPORTER_OTLP_HEADERS | - | Optional headers to send to the OTLP collector (e.g. for authentication) |
| OTEL_RESOURCE_ATTRIBUTES | - | Resource attributes attached to all spans (e.g. `service.name=service-print-api`) |
| OTEL_PYTHON_EXCLUDED_URLS | - | Comma-separated list of URL patterns to exclude from tracing (e.g. `checker`) |

#### Local tracing setup

To test tracing locally, start the OTEL collector and Zipkin:

```bash
docker compose -f docker-compose-otel.yml up -d
```

Then start the app with `make gunicornserve`. Traces are visible at **<http://localhost:9411>** (Zipkin UI).

