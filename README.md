# service-print-api

| Branch | Status |
|--------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiNXRGbGtlM2FoVXVNTElKVmRybVB4QTdab2dzUi9sUzN5ZGJ2eU1XeVY3Qjc0bFRJbDhVWkZPK2M1ZVZpQ3RZMDdRbDNBM2tMZmJXUG5VcjF4QnBJdmo4PSIsIml2UGFyYW1ldGVyU3BlYyI6IlNTbndCOTdHVDVxaEQ0MlAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) [![codecov-develop](https://codecov.io/gh/swissgeo/service-print-api/branch/develop/graph/badge.svg)](https://codecov.io/gh/swissgeo/service-print-api) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiNXRGbGtlM2FoVXVNTElKVmRybVB4QTdab2dzUi9sUzN5ZGJ2eU1XeVY3Qjc0bFRJbDhVWkZPK2M1ZVZpQ3RZMDdRbDNBM2tMZmJXUG5VcjF4QnBJdmo4PSIsIml2UGFyYW1ldGVyU3BlYyI6IlNTbndCOTdHVDVxaEQ0MlAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) [![codecov-main](https://codecov.io/gh/swissgeo/service-print-api/branch/main/graph/badge.svg)](https://codecov.io/gh/swissgeo/service-print-api) |

## Table of Content

- [Table of Content](#table-of-content)
- [Summary Of The Project](#summary-of-the-project)
- [Service API](#service-api)
- [API Documentation](#api-documentation)
- [Versioning](#versioning)
- [Local Development](#local-development)
  - [Dependencies](#dependencies)
  - [Setup](#setup)
  - [Accessing Local AWS Services](#accessing-local-aws-services)
  - [Updating Packages](#updating-packages)
- [Deployment configuration](#deployment-configuration)
  - [Observability](#observability)
    - [Local OTEL testing](#local-otel-testing)



## Summary Of The Project

`service-print-api` is as service that has been built to be communicating with a client, from whom its receiving print commands and putting them into a queue to be processed. Most probably this client is the new webmapviewer of swissgeo.

After a client has POSTed (HTTP POST) a print command `service-print-api` returns an answer with an ID of this specific print command. With this ID the client can ask (via HTTP GET) the `service-print-api` about the status of the print.

As soon as the print has been accomplished, the client recives a positive status with a link to download the created pdf document.

## Service API

[Here the REST API specification](https://swissgeoplatform.atlassian.net/wiki/spaces/PB/pages/105218145/Communication), which has been implemented as described.

Furthermore there exists the checker GET endpoint to test, if the server is up:

The base path is configurable via the `API_PATH_PREFIX` environment variable (default: `/api/wps/v1/print`).

| Path | Method | Argument | Response Type |
|------|--------|----------|---------------|
| `$API_PATH_PREFIX`/checker | GET | - | application/json |
| `$API_PATH_PREFIX`/jobs | POST | json (f.ex. post_print.sh) | application/json |
| `$API_PATH_PREFIX`/jobs/\<job_id\> | GET | job_id | application/json |

## API Documentation

FastAPI automatically generates an OpenAPI schema from the endpoint definitions and Pydantic models.
Each path operation defines its request parameters and responses using Pydantic models, which are
reflected directly in the generated schema. To explore the interactive documentation, start the
local server:

```bash
make serve
```

Then open:

- [http://localhost:3000/docs](http://localhost:3000/docs) - Swagger UI (interactive)
- [http://localhost:3000/redoc](http://localhost:3000/redoc) - ReDoc

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

To start the local AWS stack for development (DynamoDB, SQS main queue + dead-letter queue, S3):

```bash
make start-moto
```

If a moto server is already running (e.g. started from `service-print-renderer`), `make start-moto` reuses it and only reruns the init containers.

### Accessing Local AWS Services

When the local stack is running, you can inspect AWS resources using the AWS CLI by pointing it at the moto server. Use the same credentials and region that the init containers use:

```bash
AWS_ACCESS_KEY_ID=123 AWS_SECRET_ACCESS_KEY=123 \
  aws sqs list-queues \
  --endpoint-url http://localhost:5000 \
  --region eu-central-1
```

The same pattern applies to other services:

```bash
# List DynamoDB tables
AWS_ACCESS_KEY_ID=123 AWS_SECRET_ACCESS_KEY=123 \
  aws dynamodb list-tables \
  --endpoint-url http://localhost:5000 \
  --region eu-central-1

# List S3 buckets
AWS_ACCESS_KEY_ID=123 AWS_SECRET_ACCESS_KEY=123 \
  aws s3api list-buckets \
  --endpoint-url http://localhost:5000 \
  --region eu-central-1
```

> **Note:** The credentials (`123`/`123`) and region (`eu-central-1`) must match what the init containers used, as moto scopes resources by account ID (derived from the access key) and region.

### Updating Packages

All packages used in production are pinned to a major version. Automatically updating these packages
will use the latest minor (or patch) version available. Packages used for development, on the other
hand, are not pinned unless they need to be used with a specific version of a production package
(for example, types-aiobotocore for aioboto3).

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
uv add fastapi~=0.135
```

## Deployment configuration

The service is configured by Environment Variable:

| Env         | Default               | Description                            |
|-------------|-----------------------|----------------------------------------|
| HTTP_PORT | `3000` | Port the HTTP server listens on |
| API_PATH_PREFIX | `/api/wps/v1/print` | Base path prefix for all API routes |
| AWS_LOCAL | `false` | Set to `true` to point AWS clients at the moto server instead of real AWS |
| MOTO_HOST | `localhost` | Hostname of the moto server (local development only) |
| MOTO_PORT | `5000` | Port of the moto server (local development only) |
| ALLOWED_DOMAINS | `.*` | Comma-separated list of regex patterns for CORS allowed origins |
| CACHE_CONTROL | `no-store` | `Cache-Control` header value for successful responses |
| CACHE_CONTROL_4XX | `public, max-age=120` | `Cache-Control` header value for 4xx error responses |
| DYNAMODB_TABLE_NAME | `service-print-jobs-local` | The name of the DynamoDB table storing print job info |
| S3_BUCKET_NAME | `service-print-pdf-local` | Bucket holding the rendered PDFs. Only used in local dev (`AWS_LOCAL=true`) to build a `pdfUrl` pointing directly at the moto S3 object; in prod the ingress serves `<api_path_prefix>/pdf/<job_id>.pdf` from the bucket. Must match the renderer's `S3_BUCKET_NAME`. |
| S3_PDF_PREFIX | `api/wps/v1/print/pdf` | Key prefix under which the renderer uploads PDFs (`<prefix>/<job_id>.pdf`). Used with `S3_BUCKET_NAME` to build the local-dev `pdfUrl`. Must match the renderer's `S3_PDF_PREFIX`. |
| SQS_QUEUE_NAME | `service-print-jobs-queue-local` | The name of the SQS queue |
| SQS_DL_QUEUE_NAME | `service-print-jobs-dlq-local` | The name of the SQS dead-letter queue |
| SQS_MAX_RECEIVE_COUNT | `3` | Number of times a message can be received before SQS routes it to the DLQ automatically |
| SQS_VISIBILITY_TIMEOUT | `60` | How long (in seconds) a received message is hidden from other consumers; after expiry SQS redelivers it (or routes to DLQ if `maxReceiveCount` is reached) |
| SQS_QUEUE_MAX_LENGTH | `100` | Maximum number of messages in the queue before new print requests are rejected with 503. SQS has no built-in queue length limit, so this is an application-level throttle to prevent workers from being overwhelmed by a backlog they cannot process in time. |
| EXPIRATION_TIME_HH_PRINT_DOC | `24` | Expiration time in hours before re-generating an already existing PDF |
| TTL_DYNAMODB_ITEM_HH | `48` | Time-to-live in hours for DynamoDB items |
| AWS_CONNECT_TIMEOUT | `5` | Timeout in seconds for establishing a connection to DynamoDB/SQS |
| AWS_READ_TIMEOUT | `30` | Timeout in seconds for reading a response from DynamoDB/SQS |
| FORWARDED_ALLOW_IPS | `*` | uvicorn setting: which proxy IPs to trust for `X-Forwarded-*` headers (used to build absolute URLs like `reportUrl`/`pdfUrl`). Default `*` trusts any source and relies on k8s network policies; set to traefik's pod CIDR for a tighter allowlist |

### Observability

The service supports OpenTelemetry logging, tracing, and metrics. In production, telemetry is
exported via OTLP to an OpenTelemetry Collector (or any OTLP-compatible backend). Only the OTLP
exporter is implemented by the application. There is no console-exporter fallback.

Local development (`.env.default`) ships with OTEL **disabled**
(`OTEL_SDK_DISABLED=true`), so `make serve` uses plain console logging for a simpler dev experience.
Set `OTEL_SDK_DISABLED=false` to exercise the full pipeline locally (see
[Local OTEL testing](#local-otel-testing)).

Logs are exported using the OpenTelemetry `LoggerProvider`, which associates them with the active
trace/span context.

| Env | Default | Description |
| --- | ------- | ----------- |
| OTEL_SDK_DISABLED | `false` | Set to `true` to disable all OTEL instrumentation |
| OTEL_ENABLE_FASTAPI | `false` | Set to `true` to enable automatic tracing of FastAPI HTTP requests |
| OTEL_ENABLE_BOTO | `false` | Set to `true` to enable tracing of DynamoDB and SQS calls |
| OTEL_ENABLE_OTLP_EXPORTER | `true` | Set to `false` to disable the OTLP exporter (e.g. when no collector is running) |
| OTEL_ENABLE_METRICS | `false` | Set to `true` to enable OTLP metrics export |
| OTEL_METRIC_EXPORT_INTERVAL | `60000` | Metric export interval in ms (read by the OTEL SDK; only relevant when metrics are enabled) |
| OTEL_METRIC_EXPORT_TIMEOUT | `30000` | Metric export timeout in ms (read by the OTEL SDK; only relevant when metrics are enabled) |
| OTEL_EXPORTER_OTLP_ENDPOINT | `http://localhost:4317` | OTLP gRPC endpoint of the collector |
| OTEL_EXPORTER_OTLP_INSECURE | `false` | Set to `true` to use an insecure (non-TLS) connection to the collector |
| OTEL_EXPORTER_OTLP_HEADERS | - | Optional headers to send to the OTLP collector (e.g. for authentication) |
| OTEL_RESOURCE_ATTRIBUTES | - | Resource attributes attached to all spans (e.g. `service.name=service-print-api`) |
| OTEL_PYTHON_EXCLUDED_URLS | - | Comma-separated list of URL patterns to exclude from tracing (e.g. `checker`) |

#### Local OTEL testing

OTEL is disabled by default locally, so first enable it in `.env`:

```bash
OTEL_SDK_DISABLED=false
```

Then start the OTEL collector and Jaeger (runs detached):

```bash
make start-otel
```

Then start the app with `make serve`. Traces are visible at **<http://localhost:16686>** (Jaeger
UI); logs and metrics go to the collector's debug exporter: Follow them with:

```bash
docker compose -p service-print-local-otel -f docker-compose-otel.yml logs -f otel-collector
```

Stop the stack with `make stop-otel`.

