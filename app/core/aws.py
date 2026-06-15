from functools import lru_cache

from botocore.config import Config

from app.settings import get_settings


@lru_cache
def botocore_config() -> Config:
    settings = get_settings()
    return Config(
        connect_timeout=settings.aws_connect_timeout,
        read_timeout=settings.aws_read_timeout,
        # See https://docs.aws.amazon.com/boto3/latest/guide/retries.html for detail
        retries={"mode": "standard", "total_max_attempts": 3},
    )
