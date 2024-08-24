import os
import time
from typing import Any, Dict, List
from subprocess import check_output

from ciftag.celery_app import app
from ciftag.models import enums
from ciftag.scripts.common import insert_task_status, update_task_status
from ciftag.services.pinterest.run import run


@app.task(bind=True, name="ciftag.task.pinterest_run")
def run_pinterest(work_id: int, cred_info_list: List[Dict[str, Any]], goal_cnt: int, data: Dict[str, Any]) -> Dict[str, Any]:
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
        'body': data,
        'task_sta': enums.TaskStatusCode.load,
        'get_cnt': 0,
        'goal_cnt': goal_cnt
    }

    task_id = insert_task_status(queue_meta)

    # TODO cred_info 할당 및 재시도 관련 로직
    cred_info = cred_info_list[0]
    run(task_id, work_id, cred_info, runner_identify, goal_cnt, data)

    return {"task_id": task_id}


@app.task(bind=True, name="ciftag.task.pinterest_after")
def after_pinterest(work_id: int) -> Dict[str, Any]:
    pass