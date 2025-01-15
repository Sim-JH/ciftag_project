import json
import signal
from datetime import datetime
from typing import Literal, Dict, Any

from kafka.errors import KafkaError

import ciftag.services.pinterest.sub_task as pinterest
from ciftag.models import enums
from ciftag.settings import TIMEZONE, SERVER_TYPE, env_key
from ciftag.utils.converter import get_traceback_str
from ciftag.scripts.common import insert_sub_task_status, update_sub_task_status
from ciftag.streams.crawler.crawler_interface import CrawlConsumerBase


class SubCrawlConsumer(CrawlConsumerBase):
    """서브 크롤러"""
    def __init__(self, task_type: Literal["common", "retry"]):
        topic = (
            env_key.KAFKA_SUB_CRAWL_RETRY_TOPIC
            if task_type == "retry"
            else env_key.KAFKA_SUB_CRAWL_TOPIC
        )
        group_id = (
            "sub_crawl_retry_consumer_group"
            if task_type == "retry"
            else "sub_crawl_consumer_group"
        )
        super().__init__(
            topic=topic,
            group_id=group_id,
            log_dir="Streams/Sub_Crawler",
            auto_offset_reset="earliest",
        )

        signal.signal(
            signal.SIGALRM,
            lambda signum, frame: (_ for _ in ()).throw(TimeoutError("Task execution exceeded the time limit."))
        )

    def _handle_result(self, sub_task_id, message, result, agt_key):
        try:
            if not result['result'] and result["message"]:
                self._retry_or_fail(sub_task_id, message, result, agt_key)
                return

            # 해당 work_id에 대한 sub task complete cnt 증가
            self.redis.incrby_key(agt_key, "sub_task_complete")
            self.redis.incrby_key(agt_key, "sub_task_get", amount=result['hits'])

            # 집계 토픽으로 배치 단위 send
            result = {
                'work_id': message['work_id'],
                'info_id': message['info_id'],
                'redis_dup_key': message['redis_name'],
                'target': message['target'],
            }
            self.logs.log_data(f'Add sub task result: {result}')

            return result

        except KafkaError as e:
            self.logs.log_data(f"Failed to send message to Kafka: {e}")

    def _retry_or_fail(self, sub_task_id, message, result, agt_key):
        re_message = json.dumps(message).encode('utf-8')
        if result["message"] == "Timeout" and message["retry"] < env_key.MAX_TASK_RETRY:
            self.producer.send(env_key.KAFKA_SUB_CRAWL_RETRY_TOPIC, value=re_message).get(timeout=10)
        else:
            self.producer.send(env_key.KAFKA_SUB_CRAWL_DLQ, value=re_message).get(timeout=10)
            update_sub_task_status(sub_task_id, {
                'task_sta': enums.TaskStatusCode.failed.name,
                'msg': f"Max retry over (sub_task_id: {sub_task_id})",
            })
            self.logs.log_data(f'-- Max retry over sub_task_id: {sub_task_id}', 'error')
            self.redis.incrby_key(agt_key, "sub_task_failed")

    def _handle_timeout(self, sub_task_id, exc, agt_key):
        signal.alarm(0)
        update_sub_task_status(sub_task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'TimeOut sub_task_id: {sub_task_id} Error: {exc}',
            'traceback': get_traceback_str(exc),
        })
        self.logs.log_data(f'-- TimeOut sub_task_id: {sub_task_id} Error: {exc}', 'error')
        self.redis.incrby_key(agt_key, "task_failed")

    def _handle_unexpected_error(self, sub_task_id, exc, agt_key):
        update_sub_task_status(sub_task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'Unexpected Exception in sub_task_id: {sub_task_id}',
            'traceback': get_traceback_str(exc),
        })
        self.logs.log_data(f'-- Unexpected Exception in sub_task_id: {sub_task_id}\nError: {exc}', 'error')
        self.redis.incrby_key(agt_key, "task_failed")

    def process_message(self, message: Dict[str, Any]):
        """메세지 처리"""
        self.logs.log_data(f"Processing sub crawl message: {message}")
        message['retry'] = int(message.get('retry', 0)) + 1
        work_id = message['work_id']
        task_id = message['task_id']
        goal_cnt = message['goal_cnt']

        sub_task_meta = {
            'task_pk': task_id,
            'runner_identify': self.runner_identify,
            'task_sta': enums.TaskStatusCode.load.name,
            'body': json.dumps(message['data'], ensure_ascii=False),
            'get_cnt': 0,
            'goal_cnt': goal_cnt,
            'start_dt': datetime.now(TIMEZONE)
        }

        # sub_task 작업 로그 insert
        sub_task_id = insert_sub_task_status(sub_task_meta)
        agt_key = f"work_id:{work_id}"

        try:
            # 해당 work_id에 대한 sub task cnt 증가
            self.redis.incrby_key(agt_key, "total_sub_tasks")
            self.redis.incrby_key(agt_key, "sub_task_goal", goal_cnt)

            # 타이머 시작
            signal.alarm(env_key.TASK_TIME_OUT)

            # 실제 서브 타스크 처리 로직 수행
            self.logs.log_data(f"Pinterest Crawl Run: sub_task_id-{sub_task_id} goal_cnt-{goal_cnt}")
            result = pinterest.run(
                sub_task_id=sub_task_id,
                info_id=message['info_id'],
                runner_identify=self.runner_identify,
                data=message['data'],
                pins=message['pins'],
            )

            return self._handle_result(sub_task_id, message, result, agt_key)

        except TimeoutError as exc:
            self._handle_timeout(sub_task_id, exc, agt_key)

        except Exception as exc:
            self._handle_unexpected_error(sub_task_id, exc, agt_key)

