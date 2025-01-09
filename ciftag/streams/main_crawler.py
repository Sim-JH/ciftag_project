import json
import signal
from datetime import datetime
from typing import Dict, Any

from kafka.errors import KafkaError

import ciftag.services.pinterest.main_task as pinterest
from ciftag.models import enums
from ciftag.settings import TIMEZONE, env_key
from ciftag.utils.converter import get_traceback_str
from ciftag.scripts.common import insert_task_status, update_task_status
from ciftag.streams.interface import CrawlConsumerBase


class MainCrawlConsumer(CrawlConsumerBase):
    """메인 크롤러"""
    def __init__(self):
        super().__init__(
            topic=env_key.KAFKA_MAIN_CRAWL_TOPIC,
            group_id="main_crawl_consumer_group",
            log_dir="Streams/Main_Crawler",
            auto_offset_reset="earliest",
            max_poll_records=1,
        )

        # 타스크 타임아웃 설정
        signal.signal(
            signal.SIGALRM,
            lambda signum, frame: (_ for _ in ()).throw(TimeoutError("Task execution exceeded the time limit."))
        )

    def _chunk_pins(self, pins, chunk_size):
        for i in range(0, len(pins), chunk_size):
            yield pins[i:i + chunk_size]

    def _handle_result(self, task_id, message, result, agt_key):
        """결과 처리"""
        try:
            if not result['result'] and result["message"]:
                self._retry_or_fail(task_id, message, result, agt_key)
                return

            # 섬네일 파싱 결과를 기반으로 크롤링 할 URL를 일정 갯수 씩 분할
            chunks = self._chunk_pins(result['pins'], env_key.MAX_IMAGE_PER_SUB_TASK)
            sub_message = {
                'work_id': message['work_id'],
                'task_id': task_id,
                'info_id': message['info_id'],
                'data': message['data'],
                'redis_name': message['redis_name'],
                'target': 'pinterest',  # 마찬가지로 target 동적으로 지정
            }

            chunk_cnt = 0
            for chunk in chunks:
                sub_message.update({'goal_cnt': len(chunk), 'pins': chunk})
                self.producer.send(env_key.KAFKA_SUB_CRAWL_TOPIC, sub_message).get(timeout=10)
                chunk_cnt += 1

            self.logs.log_data(f"Task-{task_id} send sub crawl chunks: {chunk_cnt}")

            # 해당 work_id에 대한 task complete cnt 증가
            self.redis.incrby_key(agt_key, "task_complete")
            self.redis.incrby_key(agt_key, "task_get", amount=len(result['pins']))

        # topic 전송 실패
        except KafkaError as e:
            self.logs.log_data(f"Failed to send message to Kafka: {e}")

    def _retry_or_fail(self, task_id, message, result, agt_key):
        """실패 시 재시도 혹은 DLQ 전송"""
        re_message = json.dumps(message).encode('utf-8')
        if result["message"] == "Timeout" and message["retry"] < env_key.MAX_TASK_RETRY:
            self.producer.send(env_key.KAFKA_MAIN_CRAWL_TOPIC, value=re_message).get(timeout=10)
        else:
            self.producer.send(env_key.KAFKA_MAIN_CRAWL_DLQ, value=re_message).get(timeout=10)
            update_task_status(task_id, {
                'task_sta': enums.TaskStatusCode.failed.name,
                'msg': f"Max retry over (task_id: {task_id})",
            })
            self.logs.log_data(f'-- Max retry over task_id: {task_id}', 'error')
            self.redis.incrby_key(agt_key, "task_failed")

    def _handle_timeout(self, task_id, exc, agt_key):
        """타스크 수행 시간 초과 처리"""
        signal.alarm(0)  # 타이머 종료
        update_task_status(task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'TimeOut task_id: {task_id} Error: {exc}',
            'traceback': get_traceback_str(exc),
        })
        self.logs.log_data(f'-- TimeOut task_id: {task_id} Error: {exc}', 'error')
        self.redis.incrby_key(agt_key, "task_failed")

    def _handle_unexpected_error(self, task_id, exc, agt_key):
        """예상치 못한 에러 처리"""
        update_task_status(task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'Unexpected Exception in task_id: {task_id}',
            'traceback': get_traceback_str(exc),
        })
        self.logs.log_data(f'-- Unexpected Exception in task_id: {task_id}\nError: {exc}', 'error')
        self.redis.incrby_key(agt_key, "task_failed")

    def process_message(self, message: Dict[str, Any]):
        """메세지 처리"""
        self.logs.log_data(f"Processing main crawl message: {message}")
        message['retry'] = int(message.get('retry', 0)) + 1
        work_id = message['work_id']

        task_meta = {
            'work_pk': work_id,
            'runner_identify': self.runner_identify,
            'body': json.dumps(message['data'], ensure_ascii=False),
            'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
            'get_cnt': 0,
            'goal_cnt': message['goal_cnt'],
            'start_dt': datetime.now(TIMEZONE)
        }

        # 내부 작업 로그 insert
        task_id = insert_task_status(task_meta)
        # 집계용 키
        agt_key = f"work_id:{work_id}"

        try:
            # 시작 시간 설정 (해당 키에 값이 없을 경우)
            self.redis.set_nx(agt_key, 'created_at', task_meta['start_dt'].strftime('%Y-%m-%d %H:%M:%S'))
            # 해당 work_id에 대한 task cnt 증가
            self.redis.incrby_key(agt_key, "total_tasks")
            self.redis.incrby_key(agt_key, "task_goal", amount=message['goal_cnt'])

            # 타이머 시작
            signal.alarm(env_key.TASK_TIME_OUT)

            # 섬네일 크롤링 수행
            # TODO 추후 target 별 배분
            self.logs.log_data(f"Pinterest Crawl Run: task_id-{task_id} goal_cnt-{message['goal_cnt']}")
            result = pinterest.run(
                task_id=task_id,
                cred_info=message['cred_info'],
                runner_identify=self.runner_identify,
                goal_cnt=message['goal_cnt'],
                data=message['data'],
                redis_name=message['redis_name'],
            )

            # 결과 처리
            self._handle_result(task_id, message, result, agt_key)

        except TimeoutError as exc:
            self._handle_timeout(task_id, exc, agt_key)

        except Exception as exc:
            self._handle_unexpected_error(task_id, exc, agt_key)
