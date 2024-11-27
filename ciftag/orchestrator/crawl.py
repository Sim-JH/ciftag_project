import json
from typing import Any, Dict, List, Tuple, Union

import requests
from kafka import KafkaProducer

import ciftag.utils.logger as logger
from ciftag.settings import SERVER_TYPE, env_key
from ciftag.exceptions import CiftagAPIException
from ciftag.utils.crypto import CiftagCrypto
from ciftag.utils.converter import convert_enum_in_data
from ciftag.models import PinterestCrawlInfo, TumblrCrawlInfo, FlickrCrawlInfo, enums
from ciftag.integrations.sqs import SqsManger
from ciftag.web.crud.core import insert_orm
from ciftag.web.crud.common import insert_work_status, update_work_status

logs = logger.Logger(log_dir='Dispatcher')


class CrawlTriggerDispatcher:
    """작업 환경 별 트리거 분배기"""
    def __init__(self, data: Dict[str, Any]):
        self.body = data
        # 현재 db를 환경별로 별도로 사용하므로, cred_info table 각각 따로 존재 할 수 있어 pk가 아닌, cred_id+target_code로 personal 구분
        self.cred_pk_list = []
        self.cred_info_list = []

        # Kafka 관련
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.kafka_main_topic = env_key.KAFKA_MAIN_CRAWL_TOPIC

        # Enum은 호출 상위에서 검증
        self.run_on = data['run_on']
        self.target_code = data['target_code']

        # aws 실행의 경우 github action 트리거 시킬 시 terraform 환경 변수로 등록
        self.crypto = CiftagCrypto()
        self.crypto_key = self.crypto.key_gen()
        self.crypto.load_key(self.crypto_key)

    def _cal_segment(self, task_cnt):
        """실행시킬 task 수만큼 cnt를 분배"""
        remainder = self.body['cnt'] % task_cnt
        result = [self.body['cnt'] // task_cnt] * task_cnt

        for i in range(remainder):
            result[i] += 1

        result = [value for value in result if value > 0]

        return result

    def _trigger_local(self, task_body):
        # celery worker run
        segments = self._cal_segment(task_cnt=env_key.MAIN_CRAWL_PARTISION)

        # 라운드 로빈으로 작업 배분
        for idx, goal_cnt in enumerate(segments):
            task_body.update({'goal_cnt': int(goal_cnt)})

            message = {
                'task_body': task_body,
            }
            self.kafka_producer.send(
                self.kafka_main_topic,
                json.dumps(message).encode('utf-8'),
            )

        self.kafka_producer.flush()

    def _trigger_aws(self, task_body):
        # sqs put & git action trigger
        segments = self._cal_segment(task_cnt=env_key.ECS_WORKER)
        sqs_queue = SqsManger(server_type=SERVER_TYPE)

        for idx, goal_cnt in enumerate(segments):
            task_body.update({'goal_cnt': int(goal_cnt)})
            sqs_queue.put(task_body)

        # github_action 트리거
        workflow_id = "run-terraform-ecs-fargate-by-requests.yml"
        url = (f'https://api.github.com/repos/{env_key.GIT_OWNER}/{env_key.GIT_NAME}/'
               f'actions/workflows/{workflow_id}/dispatches')

        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {env_key.GIT_TOKEN}'
        }

        data = {
            'ref': 'main',
            'inputs': {
                'server_type': SERVER_TYPE,
                'run_type': f'{self.target_code.name}',
                'work_id': str(task_body['work_id']),
                'crypto_key': self.crypto.base64_covert(self.crypto_key, 'encode')
            }
        }

        response = requests.post(url, headers=headers, json=data)

        # action 트리거 실패시 purge
        if response.status_code != 204:
            sqs_queue.purge_queue()
            logs.log_data(f'Error on Trigger Github Action: {response.text}')
            raise CiftagAPIException('Fail To Trigger Github Action', 400)

    def _trigger_services(self, model, work_id, crawl_pk):
        info_id = insert_orm(
            model,
            {
                'work_pk': work_id,
                'crawl_pk': crawl_pk,
                'cred_pk_list': '/'.join(self.cred_pk_list),
                'tags': self.body['tags'],
                'cnt': self.body['cnt'],
                'hits': 0,
                'downloads': 0
            },
            returning=True
        )

        # set redis name
        redis_name = f"{SERVER_TYPE}_{self.target_code.name.capitalize()}_{work_id}"

        task_body = {
            'work_id': work_id,
            'info_id': info_id,
            'redis_name': redis_name,
            'cred_info': self.cred_info_list[0],  # TODO cred_info 분할 할당
            'data': convert_enum_in_data(self.body),  # enum 직렬화
        }

        if self.run_on == enums.RunOnCode.local:
            self._trigger_local(task_body=task_body)
        elif self.run_on == enums.RunOnCode.aws:
            self._trigger_aws(task_body=task_body)

        update_work_status(work_id, {'work_sta': enums.WorkStatusCode.trigger})

    def set_cred_info(self, user_list: List[Tuple[str:str]], crypto=True):
        """password 암호화"""
        for cred_pk, cred_id, cred_pw in user_list:
            self.cred_pk_list.append(str(cred_pk))
            self.cred_info_list.append(
                {
                    'cred_id': cred_id,
                    'cred_pw': self.crypto.encrypt_text(plaintext=cred_pw) if crypto else cred_pw
                }
            )

    def run(self, crawl_pk) -> Union[int | str]:
        work_id = insert_work_status({'work_sta': enums.WorkStatusCode.pending})

        if self.target_code == enums.CrawlTargetCode.pinterest:
            self._trigger_services(PinterestCrawlInfo, work_id, crawl_pk)
        elif self.target_code == enums.CrawlTargetCode.tumblr:
            self._trigger_services(TumblrCrawlInfo, work_id, crawl_pk)
        elif self.target_code == enums.CrawlTargetCode.flickr:
            self._trigger_services(FlickrCrawlInfo, work_id, crawl_pk)

        return work_id

