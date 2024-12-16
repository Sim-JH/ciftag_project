import os
import time
import uuid
import json
import signal
from datetime import datetime
from typing import Literal

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

import ciftag.utils.logger as logger
import ciftag.services.pinterest.sub_task as pinterest
from ciftag.models import enums
from ciftag.integrations.redis import RedisManager
from ciftag.settings import TIMEZONE, SERVER_TYPE, env_key
from ciftag.utils.converter import get_traceback_str
from ciftag.scripts.common import insert_sub_task_status, update_sub_task_status


def sub_crawl_interface(task_type: Literal["common", "retry"]):
    # 서브 컨슈머가 실행할 로직
    if task_type == "retry":
        consumer = KafkaConsumer(
            env_key.KAFKA_SUB_CRAWL_RETRY_TOPIC,
            bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
            group_id="sub_crawl_retry_consumer_group",
            client_id=str(uuid.uuid4()),
            enable_auto_commit=False,
            auto_offset_reset='earliest',  # 구독 시작 이전 메세지들도 처리 (가장 초기 메세지부터)
        )
    else:
        consumer = KafkaConsumer(
            env_key.KAFKA_SUB_CRAWL_TOPIC,
            bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
            group_id="sub_crawl_consumer_group",
            client_id=str(uuid.uuid4()),
            enable_auto_commit=False
        )
    producer = KafkaProducer(
        bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    redis_m = RedisManager()

    # 타스크 타임아웃 설정
    signal.signal(
        signal.SIGALRM,
        lambda signum, frame: (_ for _ in ()).throw(TimeoutError("Task execution exceeded the time limit."))
    )

    # 컨슈머 로깅
    runner_identify = os.getenv('POD_NAME', 'none')
    logs = logger.Logger(log_dir='Streams/Sub_Crawler', log_name=runner_identify)
    logs.log_data(f'Start sub crawl consumer: {runner_identify}')
    logs.log_data(f"Subscribed Topics: {consumer.subscription()}")

    while True:
        for attempt in range(env_key.MAX_RETRY):
            try:
                # 메세지 batch get
                messages = consumer.poll(timeout_ms=5000)
                # poll의 경우 메세지가 없다면 빈 배열 반환
                if not messages:
                    time.sleep(1)
                    continue
                break

            # 메세지 get 자체에 실패할 경우
            except KafkaError as e:
                logs.log_data(f"Get message {attempt + 1} failed: {e}")
                if attempt < env_key.MAX_RETRY - 1:
                    time.sleep(2)  # 재시도 대기
                else:
                    logs.log_data(f"Get message max retries reached. Exiting {runner_identify}")
                    consumer.close()
                    producer.close()
                    exit()
            except Exception as e:
                logs.log_data(f"UnExpect Exception get messages: {e}")
        else:
            logs.log_data(f"There are no messages in topics")
            time.sleep(60)  # 테스트 용 임시
            continue

        for topic_partition, records in messages.items():
            batch_results = []
            logs.log_data(f"Topic Partition: {topic_partition}")
            logs.log_data(f"Records: {records}")

            for message in records:
                try:
                    task_body = json.loads(message.value.decode('utf-8'))
                    task_body['retry'] = int(task_body.get('retry', 0)) + 1
                    work_id = task_body.get("work_id")
                    task_id = task_body.get("task_id")
                    info_id = task_body.get("info_id")
                    goal_cnt = task_body.get("goal_cnt")

                    sub_task_meta = {
                        'task_pk': task_id,
                        'runner_identify': runner_identify,
                        'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
                        'body': json.dumps(task_body['data'], ensure_ascii=False),
                        'get_cnt': 0,
                        'goal_cnt': goal_cnt,
                        'start_dt': datetime.now(TIMEZONE)
                    }

                    # sub_task 작업 로그 insert
                    sub_task_id = insert_sub_task_status(sub_task_meta)
                    agt_key = f"work_id:{work_id}"
                    # 해당 work_id에 대한 sub task cnt 증가
                    redis_m.incrby_key(agt_key, "total_sub_tasks")
                    redis_m.incrby_key(agt_key, "sub_task_goal", goal_cnt)

                    # 메세지 정보
                    logs.log_data(f"Message info - partition: {message.partition}, offset: {message.offset}")
                    logs.log_data(f"Processing task: {task_body}")

                    # 타이머 시작
                    signal.alarm(env_key.TASK_TIME_OUT)

                    # 실제 서브 타스크 처리 로직 수행
                    logs.log_data(f"Pinterest Crawl Run: sub_task_id-{sub_task_id} goal_cnt-{goal_cnt}")
                    result = pinterest.run(
                        sub_task_id=sub_task_id,
                        info_id=info_id,
                        runner_identify=runner_identify,
                        data=task_body['data'],
                        pins=task_body['pins'],
                    )

                    # 작업 실패 처리
                    try:
                        if not result['result'] and result["message"]:
                            if (result["message"] == "Timeout") and task_body["retry"] < env_key.MAX_TASK_RETRY:
                                # 재시도 대상일 시 재시도 토픽으로 전송
                                producer.send(env_key.KAFKA_SUB_CRAWL_RETRY_TOPIC, value=task_body).get(timeout=10)
                                continue
                            else:
                                # 재시도 횟수 초과 혹은 즉각 실패 대상 DLQ로 send
                                producer.send(env_key.KAFKA_SUB_CRAWL_DLQ, value=task_body).get(timeout=10)
                                update_sub_task_status(sub_task_id, {
                                    'task_sta': enums.TaskStatusCode.failed.name,
                                    'msg': f"Max retry over (sub_task_id: {sub_task_id})",
                                })
                                logs.log_data(
                                    f'-- Max retry over sub_task_id: {sub_task_id}',
                                    'error'
                                )
                                # TODO 추후 DLQ 처리 토픽에서 증가시키도록
                                redis_m.incrby_key(agt_key, "sub_task_failed")
                                continue

                        # 해당 work_id에 대한 sub task complete cnt 증가
                        redis_m.incrby_key(agt_key, "sub_task_complete")
                        redis_m.incrby_key(agt_key, "sub_task_get", amount=result['hits'])

                        # 집계 토픽으로 배치 단위 send
                        result = {
                            'work_id': work_id,
                            'info_id': info_id,
                            'redis_dup_key': task_body['redis_name'],  # 썸네일 중복 체크 당시 사용 키
                            'target': task_body['target'],
                        }
                        batch_results.append(result)

                    except KafkaError as e:
                        logs.log_data(f"Failed to send message to Kafka: {e}")

                except TimeoutError as exc:
                    # 타스크 수행 시간 초과
                    signal.alarm(0)  # 타이머 종료
                    update_sub_task_status(sub_task_id, {
                        'task_sta': enums.TaskStatusCode.failed.name,
                        'msg': f' TimeOut sub_task_id: {sub_task_id} Error: {exc}',
                        'traceback': get_traceback_str(exc),
                    })
                    logs.log_data(
                        f'-- TimeOut sub_task_id: {sub_task_id} Error: {exc}',
                        'error'
                    )
                    redis_m.incrby_key(agt_key, "task_failed")

                except Exception as exc:
                    # 예상치 못한 에러
                    update_sub_task_status(sub_task_id, {
                        'task_sta': enums.TaskStatusCode.failed.name,
                        'msg': f'UnExpect Exception in Pinterest Local sub_task_id: {sub_task_id}',
                        'traceback': get_traceback_str(exc),
                    })
                    logs.log_data(
                        f'-- UnExpect Exception in Pinterest Local sub_task_id: {sub_task_id}\n'
                        f'-- Error: {exc}',
                        'error'
                    )
                    redis_m.incrby_key(agt_key, "sub_task_failed")

            logs.log_data(f"Sub task send batch_results to aggregate: {len(batch_results)}")

            if len(batch_results):
                producer.send(env_key.KAFKA_AGGREGATE_CRAWL_TOPIC, batch_results).get(timeout=10)

            consumer.commit()
            logs.log_data(f"Batch commit: {len(batch_results)} messages processed.")
