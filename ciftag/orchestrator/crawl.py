import os
from typing import Any, Dict, List, Tuple, Union

from celery import chain, group, chord

from ciftag.exceptions import CiftagWorkException

from ciftag.celery_app import app
from ciftag.utils.crypto import CiftagCrypto
from ciftag.utils.converter import convert_enum_in_data
from ciftag.models import PinterestCrawlInfo, enums
from ciftag.web.crud.core import insert_orm
from ciftag.web.crud.common import insert_work_status, update_work_status


class CrawlTriggerDispatcher:
    def __init__(self, data: Dict[str, Any]):
        self.body = data
        # 현재 db를 환경별로 별도로 사용하므로, cred_info table 각각 따로 존재 할 수 있어 pk가 아닌, cred_id+target_code로 personal 구분
        self.cred_pk_list = []
        self.cred_info_list = []

        # 일단 아래 코드 Enum 검증은 됐다고 판단 TODO 검증 로직 추가
        self.run_on = data['run_on']
        self.target_code = data['target_code']

        # crypto_key의 경우 환경 변수로 주입
        # local 실행은 분리된 큐에서 실행시키지만 환경은 같으므로 그냥 등록
        # aws 실행의 경우 github action 트리거 시킬 시 전달하여 apply 환경 변수로 등록
        self.crypto = CiftagCrypto()
        self.crypto_key = self.crypto.key_gen()
        self.crypto.load_key(self.crypto_key)

    def _cal_segment(self, worker):
        remainder = self.body['cnt'] % worker
        result = [self.body['cnt'] // worker] * worker

        for i in range(remainder):
            result[i] += 1

        return result

    def _trigger_pinterest(self, work_id: int, crawl_pk: int):
        insert_orm(
            PinterestCrawlInfo,
            {
                'work_pk': work_id,
                'crawl_pk': crawl_pk,
                'cred_pk_list': '/'.join(self.cred_pk_list),
                'tags': self.body['tags'],
                'hits': 0,
                'downloads': 0
            }
        )

        tasks = []

        if self.run_on == enums.RunOnCode.local:
            # 현재 test 용도 TODO 수식 개선
            worker = 5  # task queue의 concurrency는 10으로 설정
            segments = self._cal_segment(worker=worker)
            os.environ['crypto_key'] = self.crypto_key.decode()  # 현재 celery는 동일 환경 실행

            success_s = app.signature("ciftag.callbacks.pinterest_success")
            error_s = app.signature("ciftag.callbacks.pinterest_fail")

            for idx, goal_cnt in enumerate(segments):
                run_s = app.signature(
                    "ciftag.task.pinterest_run",
                    kwargs={
                        'work_id': work_id,
                        'cred_info_list': self.cred_info_list,
                        'goal_cnt': int(goal_cnt),
                        'data': convert_enum_in_data(self.body)  # enum 직렬화
                    }
                ).set(queue='task')
                tasks.append(chain(run_s, success_s).on_error(error_s))

            # 작업 모음 실행 및 완료 후 실행될 작업 추가 (run_group = chord(tasks)(callback))
            # aws 에선 모든 컨테이너 종료 후 실행 작업 # TODO redis set 남은 것 확인 & airflow 트리거
            run_group = group(*tasks)
            chord(run_group)(
                app.signature(
                    "ciftag.task.pinterest_after",
                    kwargs={
                        'work_id': work_id
                    }
                )
            )

        elif self.run_on == enums.RunOnCode.aws:
            pass

        update_work_status(work_id, {'work_sta': enums.WorkStatusCode.trigger})

    def set_cred_info(self, user_list: List[Tuple[str:str]]):
        for cred_pk, cred_id, cred_pw in user_list:
            self.cred_pk_list.append(str(cred_pk))
            self.cred_info_list.append(
                {
                    'cred_id': cred_id,
                    'cred_pw': self.crypto.encrypt_text(plaintext=cred_pw)
                }
            )

    def run(self, crawl_pk) -> Union[int | str]:
        work_id = insert_work_status({'work_sta': enums.WorkStatusCode.pending})

        if self.target_code == enums.CrawlTargetCode.pinterest:
            self._trigger_pinterest(work_id, crawl_pk)

        return work_id

