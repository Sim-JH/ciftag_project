import time
import random
import json
import requests
from datetime import datetime
from typing import Any, Dict, List

from celery.exceptions import MaxRetriesExceededError

import ciftag.utils.logger as logger
from ciftag.settings import TIMEZONE, SERVER_TYPE, env_key
from ciftag.utils.converter import get_traceback_str
from ciftag.exceptions import CiftagWorkException
from ciftag.celery_app import app
from ciftag.models import enums
from ciftag.integrations.redis import RedisManager
from ciftag.scripts.common import insert_task_status, update_task_status
from ciftag.services.flickr import PAGETYPE
from ciftag.services.flickr.run import run

logs = logger.Logger(log_dir='Celery')


@app.task(bind=True, name="ciftag.task.flickr_run", max_retries=0)
def run_flickr(
        self, work_id: int, info_id: int, redis_name: str, cred_info: Dict[str, Any], goal_cnt: int, data: Dict[str, Any]
) -> Dict[str, Any]:
    """핀터레스트 크롤러 실행"""
    # 내부 작업 식별자 생성(worker) 및 내부 작업 로그 등록
    time.sleep(random.randrange(1, 3))
    runner_identify = f"{work_id}_{self.request.id}_{str(round(time.time() * 1000))}"

    queue_meta = {
        'work_pk': work_id,
        'runner_identify': runner_identify,
        'body': json.dumps(data, ensure_ascii=False),
        'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
        'get_cnt': 0,
        'goal_cnt': goal_cnt,
        'start_dt': datetime.now(TIMEZONE)
    }

    # 내부 작업 로그 insert
    task_id = insert_task_status(queue_meta)

    # task_id를 다른 콜백에서 접근 가능하게 추가
    self.request.task_id = task_id

    try:
        for attempt in range(env_key.MAX_RETRY):
            result = run(task_id, work_id, info_id, cred_info, runner_identify, goal_cnt, data, redis_name)

            # 작업 성공
            if result['result']:
                update_task_status(task_id, {
                    'task_sta': enums.TaskStatusCode.success.name,
                    'end_dt': result['end_dt']
                })
                return result

            # 재시도 대상
            if result['message'] == "Timeout":
                update_task_status(task_id, {'task_sta': enums.TaskStatusCode.retry.name})
                continue

            # 실패 대상
            update_task_status(task_id, {
                'task_sta': enums.TaskStatusCode.failed.name,
                'msg': f"{result['message']} (task_id: {task_id})",
                'traceback': result.get('traceback'),
            })
            raise CiftagWorkException(f"-- {PAGETYPE} {result['message']} (task_id: {task_id})", 400)

        # run 재시도 횟수를 초과한 경우
        update_task_status(task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f"Max run retry over {PAGETYPE} (task_id: {task_id})",
        })
        raise MaxRetriesExceededError

    except CiftagWorkException:
        # 직접 raise한 exception
        raise

    except MaxRetriesExceededError:
        # task 재시도 횟수를 초과 했을 경우
        update_task_status(task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'Max retry over {PAGETYPE} (task_id: {task_id})',
        })
        raise CiftagWorkException(f'-- Max task retry over {PAGETYPE} (task_id: {task_id})', 400)

    except Exception as exc:
        traceback_str = get_traceback_str(exc)
        update_task_status(task_id, {
            'task_sta': enums.TaskStatusCode.failed.name,
            'msg': f'UnExpect Exception in {PAGETYPE} Local task_id: {task_id}',
            'traceback': traceback_str,
        })
        # UnExpect Exception는 에러 원문을 traceback으로 넘기도록
        raise CiftagWorkException(
            f'-- UnExpect Exception in {PAGETYPE} Local task_id: {task_id}', 400, traceback_str=traceback_str
        )


@app.task(bind=True, name="ciftag.task.flickr_after", max_retries=0)
def after_flickr(self, results: List[Dict[str, Any]], work_id: int, info_id: int, redis_name: str):
    from ciftag.models import enums
    from ciftag.web.crud.common import update_work_status
    logs.log_data(f"--- Run {PAGETYPE} Post proc: {work_id}")

    # 외부 작업 로그 update
    update_work_status(work_id, {'work_sta': enums.WorkStatusCode.postproc})

    try:
        # redis set 비우기
        redis_m = RedisManager()
        redis_m.delete_set_from_redis(redis_name)

        # 결과 집계
        hits = 0
        elapsed_time = 0

        for result in results:
            hits += int(result['hits'])

            if (e_time := float(result['elapsed_time'])) > elapsed_time:
                elapsed_time = e_time

        airflow_param = {
            'work_id': work_id,
            'info_id': info_id,
            'target': 'flickr',
            'hits': hits,
            'elapsed_time': elapsed_time,
        }

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
        logs.log_data(f'--- Dag Run Success: {response.status_code}')
    except Exception as e:
        logs.log_data(f'--- Failed Ready To Post Proc: {e}', 'error')
