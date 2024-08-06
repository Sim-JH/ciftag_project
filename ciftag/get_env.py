import os
import json


class EnvKeys:
    """local/ecs 통합 env 파싱"""
    # aws 관련
    S3_URI: str = os.getenv("S3_URI", None)
    S3_KEY: str = os.getenv("S3_KEY", None)
    S3_SECRET: str = os.getenv("S3_SECRET", None)
    SQS_URI: str = os.getenv("SQS_URI", None)

    # redis 관련
    REDIS_HOST: str = os.getenv("REDIS_HOST", None)
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_LOCK_WAITING: int = int(os.getenv("REDIS_LOCK_WAITING", 120))
    REDIS_LOCK_BOUNDARY: int = int(os.getenv("REDIS_LOCK_BOUNDARY", 20))

    # local 관련

    # db 관련
    DB_HOST: str = os.getenv("RDB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("RDB_PORT", 3306))
    DB_USERNAME: str = os.getenv("RDB_USERNAME", None)
    DB_PASSWORD: str = os.getenv("RDB_PASSWORD", None)

    # slack 관련
    SLACK_URI: str = os.getenv("SLACK_URI", None)
    SLACK_URI_NOTICE: str = os.getenv("SLACK_URI_NOTICE", None)

