from typing import Any, Dict, List, Tuple, Union

import requests
from celery import chain, group

from ciftag.settings import SERVER_TYPE, env_key
from ciftag.exceptions import CiftagAPIException
from ciftag.celery_app import app
from ciftag.utils.crypto import CiftagCrypto
from ciftag.utils.converter import convert_enum_in_data
from ciftag.models import PinterestCrawlInfo, TumblrCrawlInfo, enums
from ciftag.integrations.sqs import SqsManger
from ciftag.web.crud.core import insert_orm
from ciftag.web.crud.common import insert_work_status, update_work_status


class CrawlTriggerDispatcher:
    """작업 환경 별 트리거 분배기"""
    def __init__(self, data: Dict[str, Any]):
        self.body = data
        # 현재 db를 환경별로 별도로 사용하므로, cred_info table 각각 따로 존재 할 수 있어 pk가 아닌, cred_id+target_code로 personal 구분
        self.cred_pk_list = []
        self.cred_info_list = []

        # 일단 아래 코드 Enum 검증은 됐다고 판단 TODO 검증 로직 추가
        self.run_on = data['run_on']
        self.target_code = data['target_code']

        # aws 실행의 경우 github action 트리거 시킬 시 전달하여 apply 환경 변수로 등록
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

    def _trigger_pinterest(self, work_id: int, crawl_pk: int):
        """작업 환경에 따른 pinterest 트리거"""
        pint_id = insert_orm(
            PinterestCrawlInfo,
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

        tasks = []

        task_body = {
            'work_id': work_id,
            'pint_id': pint_id,
            'cred_info': self.cred_info_list[0],  # TODO cred_info 분할 할당
            'data': convert_enum_in_data(self.body)  # enum 직렬화
        }

        if self.run_on == enums.RunOnCode.local:
            # celery worker run
            # 현재 test 용도 TODO 수식 개선
            segments = self._cal_segment(task_cnt=env_key.CELERY_WORKER)

            error_s = app.signature("ciftag.callbacks.task_fail")

            for idx, goal_cnt in enumerate(segments):
                task_body.update({'goal_cnt': int(goal_cnt)})

                run_s = app.signature(
                    "ciftag.task.pinterest_run",
                    kwargs=task_body
                ).set(queue='task')
                tasks.append(run_s.on_error(error_s))

            # 작업 모음 실행 및 완료 후 실행될 작업 추가 (chord(tasks)(callback)은 모든 작업 성공이 보장되어야함)
            after_task_s = app.signature(
                "ciftag.task.pinterest_after",
                kwargs={
                    'work_id': work_id,
                    'pint_id': pint_id,
                }
            )
            # aws 에선 모든 컨테이너 종료 후 실행 작업
            run_group = group(*tasks)
            run_workflow = chain(run_group, after_task_s)
            run_workflow.apply_async()

        elif self.run_on == enums.RunOnCode.aws:
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
                    'run_type': 'pinterest',
                    'crypto_key': self.crypto.base64_covert(self.crypto_key, 'encode')
                }
            }

            response = requests.post(url, headers=headers, json=data)

            # action 트리거 실패시 purge
            if response.status_code != 204:
                sqs_queue.purge_queue()
                raise CiftagAPIException('Fail To Trigger Github Action', 400)

        update_work_status(work_id, {'work_sta': enums.WorkStatusCode.trigger})

    def _trigger_tumblr(self, work_id: int, crawl_pk: int):
        """작업 환경에 따른 tumblr 트리거"""
        pint_id = insert_orm(
            TumblrCrawlInfo,
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

        tasks = []

        task_body = {
            'work_id': work_id,
            'pint_id': pint_id,
            'cred_info': self.cred_info_list[0],  # TODO cred_info 분할 할당
            'data': convert_enum_in_data(self.body)  # enum 직렬화
        }

        if self.run_on == enums.RunOnCode.local:
            # celery worker run
            # 현재 test 용도 TODO 수식 개선
            segments = self._cal_segment(task_cnt=env_key.CELERY_WORKER)

            error_s = app.signature("ciftag.callbacks.task_fail")

            for idx, goal_cnt in enumerate(segments):
                task_body.update({'goal_cnt': int(goal_cnt)})

                run_s = app.signature(
                    "ciftag.task.tumblr_run",
                    kwargs=task_body
                ).set(queue='task')
                tasks.append(run_s.on_error(error_s))

            # 작업 모음 실행 및 완료 후 실행될 작업 추가 (chord(tasks)(callback)은 모든 작업 성공이 보장되어야함)
            after_task_s = app.signature(
                "ciftag.task.tumblr_after",
                kwargs={
                    'work_id': work_id,
                    'pint_id': pint_id,
                }
            )
            # aws 에선 모든 컨테이너 종료 후 실행 작업
            run_group = group(*tasks)
            run_workflow = chain(run_group, after_task_s)
            run_workflow.apply_async()

        elif self.run_on == enums.RunOnCode.aws:
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
                    'run_type': 'tumblr',
                    'crypto_key': self.crypto.base64_covert(self.crypto_key, 'encode')
                }
            }

            response = requests.post(url, headers=headers, json=data)

            # action 트리거 실패시 purge
            if response.status_code != 204:
                sqs_queue.purge_queue()
                raise CiftagAPIException('Fail To Trigger Github Action', 400)

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
            self._trigger_pinterest(work_id, crawl_pk)
        elif self.target_code == enums.CrawlTargetCode.tumblr:
            self._trigger_tumblr(work_id, crawl_pk)

        return work_id

