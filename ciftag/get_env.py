import os
import json


class EnvKeys:
    """local/ecs 통합 env 파싱"""
    def __init__(self):
        # aws 관련
        self.S3_URI: str = os.getenv("S3_URI", None)
        self.S3_KEY: str = os.getenv("S3_KEY", None)
        self.S3_SECRET: str = os.getenv("S3_SECRET", None)

        self.SQS_URI: str = os.getenv("SQS_URI", None)
        self.SQS_DEV_URI: str = os.getenv("SQS_DEV_URI", None)
        self.SQS_KEY: str = os.getenv("SQS_KEY", None)
        self.SQS_SECRET: str = os.getenv("SQS_SECRET", None)

        # region 비용 관련 문제로 아래 설정은 로컬/ecs 이원화
        # redis 관련
        self.REDIS_HOST: str = os.getenv("REDIS_HOST", None)
        self.REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
        self.REDIS_LOCK_WAITING: int = int(os.getenv("REDIS_LOCK_WAITING", 120))
        self.REDIS_LOCK_BOUNDARY: int = int(os.getenv("REDIS_LOCK_BOUNDARY", 20))

        # db 관련
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: int = int(os.getenv("DB_PORT", 3306))
        self.DB_USERNAME: str = os.getenv("DB_USERNAME", None)
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", None)
        # endregion

        # slack 관련
        self.SLACK_URI: str = os.getenv("SLACK_URI", None)
        self.SLACK_URI_NOTICE: str = os.getenv("SLACK_URI_NOTICE", None)
