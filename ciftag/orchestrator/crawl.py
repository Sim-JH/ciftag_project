from typing import Any, Dict, List, Tuple, Union

from celery import chain, group

from ciftag.exceptions import CiftagWorkException

from ciftag.celery_app import app
from ciftag.utils.crypto import CiftagCrypto
from ciftag.models import WorkInfo, WorkInfoHistory, WorkStatusCode, PinterestCrawlInfo
from ciftag.web.crud.core import insert_orm
from ciftag.services.pinterest.run import run


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
        # local 실행은 분리된 큐에서 실행시키지만 환경은 같으므로 그냥 드록
        # aws 실행의 경우 github action 트리거 시킬 시 전달하여 apply 환경 변수로 등록
        self.crypto = CiftagCrypto()
        self.crypto_key = self.crypto.key_gen()

    def _cal_segment(self, worker):
        remainder = self.body['cnt'] % worker
        result = [self.body['cnt'] // worker] * worker

        for i in range(remainder):
            result[i] += 1

        return result

    def _trigger_pinterest(self, work_id, crawl_pk):
        # TODO pinterest 정보 등록
        insert_orm(
            PinterestCrawlInfo,
            {
                'work_pk': work_id,
                'crawl_pk': crawl_pk,
                'cred_pk_list': '/'.join(self.cred_pk_list),
                'tag': self.body['tag'],
                'hits': 0,
                'downloads': 0
            },
            True)

        tasks = []

        if self.run_on == "1":
            # 현재 test 용도 TODO 수식 개선
            worker = 5  # task queue의 concurrency는 10으로 설정
            segments = self._cal_segment(worker=worker)

            # TODO redis 할당 search의 중복 크롤링도 해결필요(redis고려)도 참조
            for idx, goal_cnt in enumerate(segments):
                run_s = app.signature(
                    "ciftag.work.run_pinterest",
                    kwargs={
                        'work_id': work_id,
                        'cred_info_list': self.cred_info_list,
                        'goal_cnt': goal_cnt,
                        'data': self.body
                    }
                ).set(queue='task')
                # TODO on_failure 추가
                tasks.append(chain(run_s))

            # TODO update work info/insert hist info 헬퍼 함수 작성하여 trigger 단계로 업데이트
            run_group = group(*tasks)
            run_group.apply_async()

        elif self.run_on == "2":
            pass

    def set_cred_info(self, user_list: List[Tuple[str:str]]):
        for cred_pk, cred_id, cred_pw in user_list:
            self.cred_pk_list.append(cred_pk)
            self.cred_info_list.append(
                {
                    'cred_id': cred_id,
                    'cred_pw': self.crypto.encrypt_text(plaintext=cred_pw)
                }
            )

    def run(self, crawl_pk) -> Union[int | str]:
        work_id = insert_orm(WorkInfo, {'work_sta': WorkStatusCode.pending}, True)
        insert_orm(WorkInfoHistory, {'work_sta': WorkStatusCode.pending})

        if self.target_code == "1":
            self.target_code(work_id,crawl_pk)

        return work_id

