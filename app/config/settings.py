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
LOCALSTACK_PORT = os.environ.get("LOCALSTACK_PORT", "4566")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")

CACHE_CONTROL = os.getenv("CACHE_CONTROL", "public, max-age=31536000")
CACHE_CONTROL_4XX = os.getenv("CACHE_CONTROL_4XX", "public, max-age=3600")

DYNAMODB_TABLE_NAME: str = str(os.environ.get("DYNAMODB_TABLE_NAME", "service-print-api"))
SQS_QUEUE_NAME: str = str(os.environ.get("SQS_QUEUE_NAME", "service-print-queue"))

EXPIRATION_TIME_HH_PRINT_DOC: int = int(os.environ.get("EXPRATION_TIME_HH_PRINT_DOC", "24"))

# AWS_LOCAL=true when running locally for development
AWS_LOCAL: str = str(os.environ.get("AWS_LOCAL", "local"))
os.environ.pop("AWS_PROFILE", None)  # to be on the safe side
os.environ.pop("AWS_ACCESS_KEY_ID", None)  # to be on the safe side
os.environ.pop("AWS_SECRET_ACCESS_KEY_ID", None)  # to be on the safe side
AWS_PROFILE = None
if AWS_LOCAL == "local":
    os.environ["AWS_ACCESS_KEY_ID"] = "123"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "123"  # dummy key  # noqa: S105
elif AWS_LOCAL == "aws_poc":
    os.environ["AWS_PROFILE"] = "swisstopo-bgdi-poc-vectortiles"
