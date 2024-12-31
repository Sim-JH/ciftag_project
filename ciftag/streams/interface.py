import os
import json
import uuid
import time
from abc import ABC, abstractmethod

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

import ciftag.utils.logger as logger
from ciftag.integrations.redis import RedisManager
from ciftag.settings import TIMEZONE, SERVER_TYPE, env_key


class CrawlConsumerBase(ABC):
    def __init__(
            self,
            topic: str,
            group_id: str,
            log_dir: str,
            auto_commit: bool = False,
            auto_offset_reset: str = 'latest',
            max_poll_records: int = 500
    ):
        self.auto_commit = auto_commit
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            client_id=str(uuid.uuid4()),
            enable_auto_commit=auto_commit,
            auto_offset_reset=auto_offset_reset,
            max_poll_records=max_poll_records
        )
        self.producer = KafkaProducer(
            bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        self.redis = RedisManager()
        self.runner_identify = os.getenv('POD_NAME', 'none')
        self.logs = logger.Logger(log_dir=log_dir, log_name=self.runner_identify)

        # 컨슈머 로깅
        self.logs.log_data(f'Start crawl consumer: {self.runner_identify}')
        self.logs.log_data(f"Subscribed Topics: {self.consumer.subscription()}")

        # 파티션 연결 체크
        self.consumer.poll(timeout_ms=100)

        for partition in self.consumer.assignment():
            current_offset = self.consumer.position(partition)
            self.logs.log_data(
                f"Assigned Partition: {partition.topic}-{partition.partition}, Current Offset: {current_offset}")

    def run(self):
        while True:
            for attempt in range(env_key.MAX_RETRY):
                try:
                    # 메세지 batch get
                    messages = self.consumer.poll(timeout_ms=5000)
                    # poll의 경우 메세지가 없다면 빈 배열 반환
                    if not messages:
                        time.sleep(1)
                        continue
                    break
                # 메세지 get 자체에 실패할 경우 (카프카 연결 실패)
                except KafkaError as e:
                    self.logs.log_data(f"Failed to poll messages (attempt {attempt + 1}): {e}")
                    if attempt < env_key.MAX_RETRY - 1:
                        time.sleep(2)
                    else:
                        self._shutdown(f"Max retries reached for polling messages. Exiting.")
                except Exception as e:
                    self.logs.log_data(f"Unexpected error during polling: {e}")
            else:
                # 재시도 횟수 초과 시까지 메세지를 가져오지 못할 경우 (토픽에 메세지 없음)
                time.sleep(60)
                continue

            for topic_partition, records in messages.items():
                self.logs.log_data(f"Processing records from topic partition: {topic_partition}")
                batch_results = []

                for record in records:
                    try:
                        # 메세지 처리
                        message = json.loads(record.value.decode("utf-8"))
                        result = self.process_message(message)

                        if result:
                            batch_results.append(result)

                    except Exception as e:
                        self.logs.log_data(f"Error processing record: {e}")

                if len(batch_results):
                    # 현재는 서브 컨슈머만 배치 단위로 집계 컨슈머로 send
                    self.producer.send(env_key.KAFKA_AGGREGATE_CRAWL_TOPIC, batch_results).get(timeout=10)
                    self.logs.log_data(f"Batch commit: {len(batch_results)} messages processed.")

                if not self.auto_commit:
                    self.consumer.commit()

    def _shutdown(self, reason: str):
        self.logs.log_data(reason)
        self.consumer.close()
        self.producer.close()
        exit()

    @abstractmethod
    def process_message(self, message):
        """ 각 컨슈머 별 메세지 처리 추상 메서드 """
        pass
