import requests
from typing import List, Dict, Any
from datetime import datetime

from ciftag.settings import TIMEZONE, env_key
from ciftag.streams.crawler.crawler_interface import CrawlConsumerBase


class AggregateConsumer(CrawlConsumerBase):
    """집계용 컨슈머"""
    def __init__(self):
        super().__init__(
            topic=env_key.KAFKA_AGGREGATE_CRAWL_TOPIC,
            group_id="aggregate_crawl_consumer_group",
            log_dir="Streams/Aggregate",
            auto_commit=True,
            max_poll_records=1,
        )

    def _get_task_status(self, agt_key):
        task_status = self.redis.get_all(agt_key)
        return {
            "total_tasks": int(task_status.get("total_tasks", 0)),
            "task_goal": int(task_status.get("task_goal", 0)),
            "task_get": int(task_status.get("task_get", 0)),
            "task_complete": int(task_status.get("task_complete", 0)),
            "task_failed": int(task_status.get("task_failed", 0)),
            "total_sub_tasks": int(task_status.get("total_sub_tasks", 0)),
            "sub_task_goal": int(task_status.get("sub_task_goal", 0)),
            "sub_task_get": int(task_status.get("sub_task_get", 0)),
            "sub_task_complete": int(task_status.get("sub_task_complete", 0)),
            "sub_task_failed": int(task_status.get("sub_task_failed", 0)),
            "created_at": str(task_status.get("created_at"))
        }
    
    def _finalize_work(self, work_id, message, task_status):
        """사용한 레디스 키 삭제 및 airflow 트리거"""
        agt_key = f"work_id:{work_id}"
        self.redis.delete_set_from_redis(agt_key)  # 상태 체크 키 삭제
        self.redis.delete_set_from_redis(message.get("redis_dup_key"))  # 중복 체크 키 삭제

        elapsed_time = (datetime.now(TIMEZONE) - datetime.strptime(
            task_status.get('created_at'), '%Y-%m-%d %H:%M:%S'
        ).replace(tzinfo=TIMEZONE)).total_seconds()  # 캐시 유지 시간 기반 소모 시간 측정

        airflow_param = {
            'work_id': work_id,
            'info_id': message.get('info_id'),
            'target': message.get('target'),
            'hits': task_status.get('sub_task_get'),
            'elapsed_time': str(elapsed_time),
        }

        self.trigger_airflow(airflow_param)

    def process_message(self, message_list: List[Dict[str, Any]]):
        for message in message_list:
            try:
                self.logs.log_data(f"Processing aggregate message: {message}")

                # work_id 기반 작업 정보 캐시 조회
                work_id = message.get("work_id")
                agt_key = f"work_id:{work_id}"
                task_status = self._get_task_status(agt_key)
                self.logs.log_data(f'task_status: {task_status}')

                main_task_total = task_status.get('total_tasks')
                main_task_complete = task_status.get('task_complete')
                main_task_failed = task_status.get('task_failed')

                sub_task_total = task_status.get('total_sub_tasks')
                sub_task_complete = task_status.get('sub_task_complete')
                sub_task_failed = task_status.get('sub_task_failed')

                if (
                        main_task_total == (main_task_complete + main_task_failed)
                ) and (
                        sub_task_total == (sub_task_complete + sub_task_failed)
                ):
                    # 작업 성공 및 후처리
                    self._finalize_work(work_id, message, task_status)
                else:
                    self.logs.log_data(
                        f"Work {work_id} is still in progress: total-{main_task_total}[complete-{main_task_complete}/failed-{main_task_failed}]"
                        f"sub task: total-{sub_task_total}[complete-{sub_task_complete}/failed-{sub_task_failed}]"
                    )

            except Exception as e:
                self.logs.log_data(f"Unexpected error processing aggregate message: {e}")

    def trigger_airflow(self, params):
        """airflow 후처리 DAG 트리거"""
        try:
            url = f"http://{env_key.AIRFLOW_URI}:{env_key.AIRFLOW_PORT}/api/v1/dags/run-after-crawl/dagRuns"
            headers = {
                "content-type": "application/json",
                "Accept": "application/json",
            }
            response = requests.post(
                url,
                json={"conf": params},
                headers=headers,
                auth=(env_key.AIRFLOW_USERNAME, env_key.AIRFLOW_PASSWORD),
                verify=False  # 인증서 검증 생략
            )
            self.logs.log_data(f"Triggered Airflow DAG: {response.status_code}")
        except Exception as e:
            self.logs.log_data(f"Failed to trigger Airflow DAG: {e}")
