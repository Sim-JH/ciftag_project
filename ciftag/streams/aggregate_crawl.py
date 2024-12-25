import os
import time
import uuid
import json
import requests
from datetime import datetime

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

import ciftag.utils.logger as logger
from ciftag.integrations.redis import RedisManager
from ciftag.settings import TIMEZONE, SERVER_TYPE, env_key


def aggregate_interface():
    consumer = KafkaConsumer(
        env_key.KAFKA_AGGREGATE_CRAWL_TOPIC,
        bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
        group_id="aggregate_crawl_consumer_group",
        client_id=str(uuid.uuid4()),
        enable_auto_commit=True,  # 집계 메세지는 오토커밋
        max_poll_records = 1  # poll 시 메세지 1개씩만 폴링
    )
    producer = KafkaProducer(
        bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    redis_m = RedisManager()

    runner_identify = os.getenv('POD_NAME', 'none')
    logs = logger.Logger(log_dir='Streams/Aggregate', log_name=runner_identify)
    logs.log_data(f'Start main crawl consumer: {runner_identify}')
    logs.log_data(f"Subscribed Topics: {consumer.subscription()}")

    for partition in consumer.assignment():
        current_offset = consumer.position(partition)
        logs.log_data(f"Assigned Partition: {partition.topic}-{partition.partition}, Current Offset: {current_offset}")

    while True:
        # 메세지 획득 시도
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
            # 메세지 정보
            logs.log_data(f"Topic Partition: {topic_partition}")
            logs.log_data(f"Records: {records}")

            for record in records:
                message_list = json.loads(record.value.decode('utf-8'))
                for message in message_list:
                    try:
                        work_id = message.get("work_id")

                        # work_id 기반 작업 정보 캐시 조회
                        work_key = f"work_id:{work_id}"
                        task_status = get_task_status(work_key, redis_m, logs)
                        logs.log_data(f'task_status: {task_status}')

                        main_task_total = task_status.get('total_tasks')
                        main_task_complete = task_status.get('task_complete')
                        main_task_failed = task_status.get('task_failed')

                        sub_task_total = task_status.get('total_sub_tasks')
                        sub_task_complete = task_status.get('sub_task_complete')
                        sub_task_failed = task_status.get('sub_task_failed')

                        if (
                                main_task_total == (main_task_complete+main_task_failed)
                        ) and (
                                sub_task_total == (sub_task_complete+sub_task_failed)
                        ):
                            # 작업 성공 및 후처리
                            redis_m.delete_set_from_redis(work_key)  # 상태 체크 키 삭제
                            redis_m.delete_set_from_redis(message.get("redis_dup_key"))  # 중복 체크 키 삭제
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

                            logs.log_data(f'Send airflow_param: {airflow_param}')

                            # 후처리 트리거
                            try:
                                url = f"http://{env_key.AIRFLOW_URI}:{env_key.AIRFLOW_PORT}/api/v1/dags/run-after-crawl/dagRuns"
                                headers = {
                                    "content-type": "application/json",
                                    "Accept": "application/json",
                                }
                                response = requests.post(
                                    url,
                                    json={"conf": airflow_param},
                                    headers=headers,
                                    auth=(env_key.AIRFLOW_USERNAME, env_key.AIRFLOW_PASSWORD),
                                    verify=False  # crt 인증서 airflow 적용 시 수정 & https
                                )
                                logs.log_data(f"--- Exit dag Success: {response.status_code}")
                            except Exception as e:
                                logs.log_data(f"--- Exit dag Fail: {e}")

                        else:
                            # 작업 진행중 처리
                            logs.log_data(
                                f"Work {work_id} is progress task {main_task_total}-{main_task_complete}:{main_task_failed} "
                                f"sub task {sub_task_total}-{sub_task_complete}:{sub_task_failed}"
                            )
                            continue

                        redis_m.incrby_key(work_key, "checked_msg")
                    except Exception as e:
                        logs.log_data(f"--- Unexpected Exception: {e}")


def get_task_status(work_key, redis_client, logs):
    """ Redis Hash에서 작업 상태를 가져오기 """
    # Redis에서 모든 필드 가져오기
    task_status = redis_client.get_all(work_key)

    logs.log_data(task_status)

    # 각 필드 값 변환
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
