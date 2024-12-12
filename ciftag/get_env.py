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

        # kafka 관련
        self.KAFKA_BOOTSTRAP_SERVERS: str = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "kafka.kafka.svc.cluster.local:9092"
        )
        self.KAFKA_MAIN_CRAWL_TOPIC: str = os.getenv("KAFKA_MAIN_CRAWL_TOPIC", "main_crawl_task_topic")
        self.KAFKA_MAIN_CRAWL_DLQ: str = os.getenv("KAFKA_MAIN_CRAWL_DLQ", "main_crawl_task_dlq")
        self.KAFKA_SUB_CRAWL_TOPIC: str = os.getenv("KAFKA_SUB_CRAWL_TOPIC", "sub_crawl_task_topic")
        self.KAFKA_SUB_CRAWL_DLQ: str = os.getenv("KAFKA_SUB_CRAWL_DLQ", "sub_crawl_task_dlq")
        self.KAFKA_SUB_CRAWL_RETRY_TOPIC: str = os.getenv("KAFKA_SUB_CRAWL_RETRY_TOPIC", "sub_crawl_retry_task_topic")
        self.KAFKA_AGGREGATE_CRAWL_TOPIC: str = os.getenv("KAFKA_AGGREGATE_CRAWL_TOPIC", "agt_crawl_task_topic")
        # endregion

        # elasticsearch 관련
        self.ES_HOST: str = os.getenv("ES_HOST", 'localhost')
        self.ES_PORT: int = int(os.getenv("ES_PORT", 9200))
        self.ES_SCHEME: str = os.getenv("ES_SCHEME", "http")

        # git action 관련
        self.GIT_TOKEN: str = os.getenv("GIT_TOKEN", None)
        self.GIT_OWNER: str = os.getenv("GIT_OWNER", None)
        self.GIT_NAME: str = os.getenv("GIT_NAME", None)

        # airflow 관련
        self.AIRFLOW_URI: str = os.getenv("AIRFLOW_URI", None)
        self.AIRFLOW_PORT: int = int(os.getenv("AIRFLOW_PORT", 8080))
        self.AIRFLOW_USERNAME: str = os.getenv("AIRFLOW_USERNAME", None)
        self.AIRFLOW_PASSWORD: str = os.getenv("AIRFLOW_PASSWORD", None)

        # slack 관련
        self.SLACK_URI: str = os.getenv("SLACK_URI", None)
        self.SLACK_URI_NOTICE: str = os.getenv("SLACK_URI_NOTICE", None)

        # 작업 관련
        self.MAX_RETRY: int = os.getenv("MAX_RETRY", 3)
        self.MAX_TASK_RETRY: int = os.getenv("MAX_TASK_RETRY", 3)
        self.TASK_TIME_OUT: int = os.getenv("MAX_TASK_TIME_OUT", 2*60*60)
        self.MAX_IMAGE_PER_SUB_TASK: int = os.getenv("MAX_IMAGE_PER_SUB_TASK", 10)
        # self.CELERY_WORKER: int = os.getenv("CELERY_WORKER", 10)
        self.MAIN_CRAWL_PARTISION: int = os.getenv("MAIN_CRAWL_PARTISION", 10)
        self.SUB_CRAWL_PARTISION: int = os.getenv("SUB_CRAWL_PARTISION", 100)
        self.AGGREGATE_CRAWL_PARTISION: int = os.getenv("AGGREGATE_CRAWL_PARTISION", 5)
        self.ECS_WORKER: int = os.getenv("ECS_WORKER", 10)
