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



## Summary Of The Project

`service-print-api` is as service that has been build to be communicating with a client, from whom its receiving print commands and putting them into a queue to be processed. Most probably this client is the new webmapviewer of swissgeo.

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
| DYNAMODB_TABLE_NAME | `'service-print-headless'` | The name of the dynamodb table with the info about pdf generation|
| SQS_QUEUE_NAME | `service-print-queue` | The name of the sqs queue |
| EXPIRATION_TIME_HH_PRINT_DOC | `24` | If a pdf already has been generated, the expiration time in hours before generating a new one |
| AWS_LOCAL | - | Used for local development. Can be `local` for completely local development, `aws_poc` to interact with the aws poc accunt (will be deleted once) or nothing for a setup in a k8s environment. |

