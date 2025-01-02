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


#
# def main_crawl_interface():
#     # 메인 컨슈머가 실행할 로직
#     # TODO 각 컨슈머 로직 모두 구현 완료하면 로깅과 연결 부분 리팩토링
#     consumer = KafkaConsumer(
#         env_key.KAFKA_MAIN_CRAWL_TOPIC,
#         bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
#         group_id="main_crawl_consumer_group",
#         client_id=str(uuid.uuid4()),
#         enable_auto_commit=False,
#         auto_offset_reset='earliest',  # 구독 시작 이전 메세지들도 처리 (가장 초기 메세지부터)
#         max_poll_records=1  # poll 시 메세지 1개씩만 폴링
#     )
#     producer = KafkaProducer(
#         bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
#         value_serializer=lambda v: json.dumps(v).encode('utf-8')
#     )
#
#     redis_m = RedisManager()
#
#     # 타스크 타임아웃 설정
#     signal.signal(
#         signal.SIGALRM,
#         lambda signum, frame: (_ for _ in ()).throw(TimeoutError("Task execution exceeded the time limit."))
#     )
#
#     # 컨슈머 로깅
#     runner_identify = os.getenv('POD_NAME', 'none')
#     logs = logger.Logger(log_dir='Streams/Main_Crawler', log_name=runner_identify)
#     logs.log_data(f'Start main crawl consumer: {runner_identify}')
#     logs.log_data(f"Subscribed Topics: {consumer.subscription()}")
#
#     # 파티션 연결 체크
#     consumer.poll(timeout_ms=100)
#
#     for partition in consumer.assignment():
#         current_offset = consumer.position(partition)
#         logs.log_data(f"Assigned Partition: {partition.topic}-{partition.partition}, Current Offset: {current_offset}")
#
#     def chunk_pins(pins, chunk_size):
#         for i in range(0, len(pins), chunk_size):
#             yield pins[i:i + chunk_size]
#
#     while True:
#         for attempt in range(env_key.MAX_RETRY):
#             try:
#                 # 메세지 batch get
#                 messages = consumer.poll(timeout_ms=1000)
#                 # poll의 경우 메세지가 없다면 빈 배열 반환
#                 if not messages:
#                     time.sleep(1)
#                     continue
#                 break
#
#             # 메세지 get 자체에 실패할 경우 (카프카 연결 실패)
#             except KafkaError as e:
#                 logs.log_data(f"Get message {attempt + 1} failed: {e}")
#                 if attempt < env_key.MAX_RETRY - 1:
#                     time.sleep(2)  # 연결 재시도 대기
#                 else:
#                     logs.log_data(f"Get message max retries reached. Exiting {runner_identify}")
#                     consumer.close()
#                     producer.close()
#                     exit()
#             except Exception as e:
#                 logs.log_data(f"UnExpect Exception get messages: {e}")
#         else:
#             # 재시도 횟수 초과 시까지 메세지를 가져오지 못할 경우
#             logs.log_data(f"There are no messages in topics")
#             time.sleep(60)  # 테스트 용 임시
#             continue
#
#         for topic_partition, records in messages.items():
#             # 메세지 정보
#             logs.log_data(f"Topic Partition: {topic_partition}")
#             logs.log_data(f"Records: {records}")
#             for message in records:
#                 try:
#                     task_body = json.loads(message.value.decode('utf-8')).get('task_body')
#                     task_body['retry'] = int(task_body.get('retry', 0)) + 1
#                     work_id = task_body['work_id']
#                     info_id = task_body['info_id']
#
#                     task_meta = {
#                         'work_pk': work_id,
#                         'runner_identify': runner_identify,
#                         'body': json.dumps(task_body['data'], ensure_ascii=False),
#                         'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
#                         'get_cnt': 0,
#                         'goal_cnt': task_body['goal_cnt'],
#                         'start_dt': datetime.now(TIMEZONE)
#                     }
#
#                     # 내부 작업 로그 insert
#                     task_id = insert_task_status(task_meta)
#                     # 집계용 키
#                     agt_key = f"work_id:{work_id}"
#                     # 시작 시간 설정 (해당 키에 값이 없을 경우)
#                     redis_m.set_nx(agt_key, 'created_at', task_meta['start_dt'].strftime('%Y-%m-%d %H:%M:%S'))
#                     # 해당 work_id에 대한 task cnt 증가
#                     redis_m.incrby_key(agt_key, "total_tasks")
#                     redis_m.incrby_key(agt_key, "task_goal", amount=task_body['goal_cnt'])
#
#                     # 타이머 시작
#                     signal.alarm(env_key.TASK_TIME_OUT)
#
#                     # 섬네일 크롤링 수행
#                     # TODO 추후 target 별 배분
#                     logs.log_data(f"Pinterest Crawl Run: task_id-{task_id} goal_cnt-{task_body['goal_cnt']}")
#                     result = pinterest.run(
#                         task_id=task_id,
#                         cred_info=task_body['cred_info'],
#                         runner_identify=runner_identify,
#                         goal_cnt=task_body['goal_cnt'],
#                         data=task_body['data'],
#                         redis_name=task_body['redis_name'],
#                     )
#
#                     # 작업 실패 처리
#                     try:
#                         if not result['result'] and result["message"]:
#                             message = json.dumps(task_body).encode('utf-8')
#                             if (result["message"] == "Timeout") and task_body["retry"] < env_key.MAX_TASK_RETRY:
#                                 # 재시도 대상의 경우 일정 시간 대기 후 토픽에 다시 push
#                                 # main task의 경우 재시도는 따로 재시도 토픽으로 분리 x. 다만 task 부하가 심해질 경우 재시도 토픽 별도 분리.
#                                 producer.send(env_key.KAFKA_MAIN_CRAWL_TOPIC, value=message).get(timeout=10)
#                                 continue
#                             else:
#                                 # 재시도 횟수 초과 혹은 즉각 실패 대상 DLQ로 send
#                                 producer.send(env_key.KAFKA_MAIN_CRAWL_DLQ, value=message).get(timeout=10)
#                                 update_task_status(task_id, {
#                                     'task_sta': enums.TaskStatusCode.failed.name,
#                                     'msg': f"Max retry over (task_id: {task_id})",
#                                 })
#                                 logs.log_data(
#                                     f'-- Max retry over task_id: {task_id}',
#                                     'error'
#                                 )
#                                 # TODO 추후 DLQ 처리 토픽에서 증가시키도록
#                                 redis_m.incrby_key(agt_key, "task_failed")
#                                 continue
#
#                         # 섬네일 파싱 결과를 기반으로 크롤링 할 URL를 일정 갯수 씩 분할
#                         chunks = chunk_pins(result['pins'], env_key.MAX_IMAGE_PER_SUB_TASK)
#                         message = {
#                             'work_id': work_id,
#                             'task_id': task_id,
#                             'info_id': info_id,
#                             'data': task_body['data'],
#                             'redis_name': task_body['redis_name'],
#                             'target': 'pinterest'  # 마찬가지로 target 동적으로 지정
#                         }
#
#                         # 해당 work_id에 대한 task complete cnt 증가
#                         redis_m.incrby_key(agt_key, "task_complete")
#                         redis_m.incrby_key(agt_key, "task_get", amount=len(result['pins']))
#
#                         # sub topic으로 send
#                         chunk_cnt = 0
#                         for chunk in chunks:
#                             message.update({'goal_cnt': len(chunk), 'pins': chunk})
#                             producer.send(env_key.KAFKA_SUB_CRAWL_TOPIC, message).get(timeout=10)
#                             chunk_cnt += 1
#
#                         logs.log_data(f"Task-{task_id} send sub crawl chunks: {chunk_cnt}")
#
#                     # topic 전송 실패
#                     except KafkaError as e:
#                         logs.log_data(f"Failed to send message to Kafka: {e}")
#
#                 except TimeoutError as exc:
#                     # 타스크 수행 시간 초과
#                     signal.alarm(0)  # 타이머 종료
#                     update_task_status(task_id, {
#                         'task_sta': enums.TaskStatusCode.failed.name,
#                         'msg': f' TimeOut task_id: {task_id} Error: {exc}',
#                         'traceback': get_traceback_str(exc),
#                     })
#                     logs.log_data(
#                         f'-- TimeOut task_id: {task_id} Error: {exc}',
#                         'error'
#                     )
#                     redis_m.incrby_key(agt_key, "task_failed")
#
#                 except Exception as exc:
#                     # 예상치 못한 에러
#                     update_task_status(task_id, {
#                         'task_sta': enums.TaskStatusCode.failed.name,
#                         'msg': f'UnExpect Exception in Pinterest Local task_id: {task_id}',
#                         'traceback': get_traceback_str(exc),
#                     })
#                     logs.log_data(
#                         f'-- UnExpect Exception in Pinterest Local task_id: {task_id}\n'
#                         f'-- Error: {exc}',
#                         'error'
#                     )
#                     redis_m.incrby_key(agt_key, "task_failed")
#
#             # 오프셋 커밋
#             consumer.commit()
#
#
