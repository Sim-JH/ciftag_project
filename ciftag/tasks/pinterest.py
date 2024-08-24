import os
import time
import json
from datetime import datetime
from typing import Any, Dict, List
from subprocess import check_output

from celery.exceptions import MaxRetriesExceededError

from ciftag.settings import TIMEZONE
from ciftag.exceptions import CiftagWorkException
from ciftag.celery_app import app
from ciftag.models import enums
from ciftag.scripts.common import insert_task_status, update_task_status
from ciftag.services.pinterest.run import run


@app.task(bind=True, name="ciftag.task.pinterest_run", max_retries=3, default_retry_delay=30)
def run_pinterest(
        self, work_id: int, cred_info_list: List[Dict[str, Any]], goal_cnt: int, data: Dict[str, Any]
) -> Dict[str, Any]:
    """핀터레스트 크롤러 실행"""
    # 내부 작업 식별자 생성 및 내부 작업 로그 등록
    host_name = check_output(["hostname"]).strip().decode("utf-8").replace("-", ".")

    try:
        real_ip = (
            check_output(["curl", "-s", "https://lumtest.com/myip"])
            .decode("utf-8")
            .replace("-", ".")
        )
    except Exception:
        real_ip = "ip_error"

    runner_identify = f"{work_id}_{host_name}_{real_ip}_{str(round(time.time() * 1000))}"

    queue_meta = {
        'work_pk': work_id,
        'runner_identify': runner_identify,
        'body': json.dumps(data),
        'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
        'get_cnt': 0,
        'goal_cnt': goal_cnt,
        'start_dt': datetime.now(TIMEZONE)
    }

    task_id = insert_task_status(queue_meta)

    # TODO cred_info 할당 및 재시도 관련 로직
    # TODO 작업 실행 관련 최상위 try except. 여기서 에러 처리 관리. on_error에 task_id 전달해줘야함
    # try:
    cred_info = cred_info_list[0]
    run(task_id, work_id, cred_info, runner_identify, goal_cnt, data)
    # except Exception as exc:
    #     retries = self.request.retries
    #     try:
    #         self.retry(exc=exc, kwargs={'task_id': task_id})
    #     except MaxRetriesExceededError:
    #         # 재시도 횟수를 초과했을 때
    #         print("Max retries exceeded.")
    #
    #     raise CiftagWorkException('Error On Local Process',  enums.TaskStatusCode.failed, task_id=task_id) from exc
    #
    # return {"task_id": task_id}
    #

@app.task(bind=True, name="ciftag.task.pinterest_after")
def after_pinterest(work_id: int) -> Dict[str, Any]:
    #pinterest 테이블 업데이트
    #work테이블 업데이트
    pass