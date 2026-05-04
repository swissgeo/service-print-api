import os

"""
The Config contains everything needed to run the service. Most entries have a default
value and an environment value to override it.

"""
ENV_FILE = os.getenv("ENV_FILE", None)
if ENV_FILE:
    from dotenv import load_dotenv

    print(f"Running locally hence injecting env vars from {ENV_FILE}")  # noqa: T201
    load_dotenv(ENV_FILE, override=True, verbose=True)


# Definition of the allowed domains for CORS implementation
ALLOWED_DOMAINS_STRING = os.getenv("ALLOWED_DOMAINS", ".*")
ALLOWED_DOMAINS = ALLOWED_DOMAINS_STRING.split(",")
ALLOWED_DOMAINS_PATTERN = f"({'|'.join(ALLOWED_DOMAINS)})"
MOTO_HOST = os.environ.get("MOTO_HOST", "localhost")
MOTO_PORT = os.environ.get("MOTO_PORT", "5000")
MOTO_ENDPOINT = f"http://{MOTO_HOST}:{MOTO_PORT}"
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")

CACHE_CONTROL = os.getenv("CACHE_CONTROL", "no-store")
CACHE_CONTROL_4XX = os.getenv("CACHE_CONTROL_4XX", "public, max-age=120")

DYNAMODB_TABLE_NAME: str = str(os.environ.get("DYNAMODB_TABLE_NAME", "service-print-jobs-local"))
SQS_QUEUE_NAME: str = str(os.environ.get("SQS_QUEUE_NAME", "service-print-jobs-queue-local"))

EXPIRATION_TIME_HH_PRINT_DOC: int = int(os.environ.get("EXPIRATION_TIME_HH_PRINT_DOC", "24"))
SQS_QUEUE_MAX_LENGTH: int = int(os.environ.get("SQS_QUEUE_MAX_LENGTH", "100"))
AWS_CONNECT_TIMEOUT: int = int(os.environ.get("AWS_CONNECT_TIMEOUT", "5"))
AWS_READ_TIMEOUT: int = int(os.environ.get("AWS_READ_TIMEOUT", "30"))
TTL_DYNAMODB_ITEM_HH: int = int(os.environ.get("TTL_DYNAMODB_ITEM_HH", "48"))
MAX_PAYLOAD_SIZE_BYTES: int = int(os.environ.get("MAX_PAYLOAD_SIZE_BYTES", str(100 * 1024)))
API_PATH_PREFIX: str = os.getenv("API_PATH_PREFIX", "/api/wps/v1/print")

# AWS_LOCAL
AWS_LOCAL: bool = os.environ.get("AWS_LOCAL", "false").lower() == "true"
if AWS_LOCAL:
    os.environ["AWS_ACCESS_KEY_ID"] = "123"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "123"  # dummy key  # noqa: S105
