import os
import json


class EnvKeys:
    # aws 관련
    S3_URI: str = os.getenv("S3_URI")
    S3_KEY: str = os.getenv("S3_KEY")
    S3_SECRET: str = os.getenv("S3_SECRET")
    SQS_URI: str = os.getenv("SQS_URI")

    # redis 관련
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT"))
    REDIS_LOCK_WAITING: int = int(os.getenv("REDIS_LOCK_WAITING", 120))
    REDIS_LOCK_BOUNDARY: int = int(os.getenv("REDIS_LOCK_BOUNDARY", 20))

    # local 관련

    # db 관련
    DB_HOST: str = os.getenv("RDB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("RDB_PORT", 3306))
    DB_USERNAME: str = os.getenv("RDB_USERNAME")
    DB_PASSWORD: str = os.getenv("RDB_PASSWORD")

    # logging 관련
    LOG_PATH: str = os.getenv("LOG_PATH")
    SLACK_URI: str = os.getenv("SLACK_URI")
    SLACK_URI_NOTICE: str = os.getenv("SLACK_URI_NOTICE")

