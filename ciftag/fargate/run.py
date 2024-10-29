"""
ECS container가 실행 -> 지속적으로 sqs를 pop -> 모든 작업 수행 완료 후 exit_handler로 종료처리
"""
import sys
import time
import random
import json
import atexit
import requests
from datetime import datetime
from subprocess import check_output

import ciftag.utils.logger as logger
import ciftag.services.pinterest.run as pinterest
import ciftag.services.tumblr.run as tumblr
import ciftag.services.flickr.run as flickr
from ciftag.settings import SERVER_TYPE, TIMEZONE, env_key
from ciftag.models import enums
from ciftag.utils.converter import get_traceback_str
from ciftag.integrations.sqs import SqsManger
from ciftag.integrations.redis import RedisManager
from ciftag.scripts.common import check_task_status, aggregate_task_result, insert_task_status, update_task_status

logs = logger.Logger('AWS')


def exit_handler():
    global _work_id
    result = check_task_status(work_id=_work_id)

    # work_id == ecs task 그룹 / 각 task는 대상 사이트를 1개씩만 할당
    # if 현재 컨테이너가 실행 중인 ecs 중 마자막일 경우
    if result is None or len(result) == 0:
        global REDIS_NAME
        redis_m = RedisManager()
        redis_m.delete_set_from_redis(REDIS_NAME)

        task_result = aggregate_task_result(work_id=_work_id)

        # TODO airflow 상위 task dag 구현 이후 동적 호출 방법 수정
        for target, get_cnt, elapsed_time in task_result:
            airflow_param = {
                'work_id': _work_id,
                'hits': get_cnt,
                'target': target,
                'elapsed_time': elapsed_time,
            }

            try:
                url = f"http://{env_key.AIRFLOW_URI}:{env_key.AIRFLOW_PORT}/api/v1/dags/rrun-after-crawl/dagRuns"
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


_work_id = 0

try:
    real_ip = (
        check_output(["curl", "-s", "https://lumtest.com/myip"])
        .decode("utf-8")
        .replace("-", ".")
    )
except Exception as e:
    real_ip = "ip_error"

host_name = check_output(["hostname"]).strip().decode("utf-8").replace("-", ".")
runner_identify = f"{real_ip}_{host_name}_{str(round(time.time() * 1000))}"
REDIS_NAME = ""


def runner(run_type: str, container_work_id: int):
    atexit.register(exit_handler)  # 프로세스 종료시 호출

    # container별 log_name 지정 필요하려나?
    # container_ip = check_output(["curl", "https://lumtest.com/myip"])
    global _work_id
    container_start_time = time.time()
    _work_id = container_work_id

    re_call = 0  # get sqs 시도 횟수
    loop_count = 0  # 현 컨테이너의 작업 횟수
    vpn_log_flag = False

    while True:
        time.sleep(random.randrange(1, 3))

        sqs_queue = SqsManger(server_type=SERVER_TYPE)
        content = sqs_queue.get()

        # get sqs 실패 시 n회까지 재시도
        if not content:
            if re_call < env_key.MAX_RETRY:
                re_call += 1
                logs.log_data(f"SQS Recall: {str(re_call)}")
                time.sleep(10)
            else:
                logs.log_data(f"Not Found SQS")
                break

        else:
            logs.log_data(f"--- Get SQS Content : {str(content)}")

            if _retry := content.get('retry'):
                content['retry'] = int(_retry)+1
            else:
                content['retry'] = 1

            re_call = 1
            sqs_queue.delete()

            global REDIS_NAME
            REDIS_NAME = content['redis_name']

            work_id = content['work_id']
            goal_cnt = content['goal_cnt']

            if container_work_id and container_work_id != int(work_id):
                # container를 실행시킨 work_id와 가져온 queue의 work_id가 다를 경우 pass
                # 동시 작업의 경우 더 나은 방법 고려해보기
                sqs_queue.put(content)

            # 내부 작업 로그 insert
            queue_meta = {
                'work_pk': work_id,
                'runner_identify': runner_identify,
                'body': json.dumps(content['data'], ensure_ascii=False),
                'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
                'get_cnt': 0,
                'goal_cnt': goal_cnt,
                'start_dt': datetime.now(TIMEZONE)
            }

            task_id = insert_task_status(queue_meta)

            if loop_count == 0:
                vpn_log_flag = True  # 한 번이라도 queue 소비한 컨테이너인지 체크

            logs.log_data(f"{runner_identify} SQS loop count : {loop_count}")

            try:
                if run_type == "pinterest":
                    result = pinterest.run(
                        task_id,
                        work_id,
                        content['info_id'],
                        content['cred_info'],
                        runner_identify,
                        goal_cnt,
                        content['data'],
                        REDIS_NAME
                    )
                elif run_type == "tumblr":
                    result = tumblr.run(
                        task_id,
                        work_id,
                        content['info_id'],
                        content['cred_info'],
                        runner_identify,
                        goal_cnt,
                        content['data'],
                        REDIS_NAME
                    )
                elif run_type == "flicker":
                    result = flickr.run(
                        task_id,
                        work_id,
                        content['info_id'],
                        content['cred_info'],
                        runner_identify,
                        goal_cnt,
                        content['data'],
                        REDIS_NAME
                    )
                else:
                    # debug용 컨테이너
                    while True:
                        time.sleep(60*60*3)

                # 실패 시 큐 재삽입
                if not result['result'] and result["message"]:
                    if result["message"] == "Timeout":
                        # 재시도 대상
                        if int(content["retry"]) < 3:
                            sqs_queue.put(content)
                        else:
                            # 재시도 횟수를 초과한 경우
                            update_task_status(task_id, {
                                'task_sta': enums.TaskStatusCode.failed.name,
                                'msg': f"Max retry over (task_id: {task_id})",
                            })

                            logs.log_data(
                                f'-- Max retry over task_id: {task_id}',
                                'error'
                            )
                    else:
                        # 실패 대상
                        update_task_status(task_id, {
                            'task_sta': enums.TaskStatusCode.failed.name,
                            'msg': f"{result['message']} (task_id: {task_id})",
                            'traceback': result.get('traceback'),
                        })

            except Exception as exc:
                # 예상치 못한 에러
                update_task_status(task_id, {
                    'task_sta': enums.TaskStatusCode.failed.name,
                    'msg': f'UnExpect Exception in Pinterest Local task_id: {task_id}',
                    'traceback': get_traceback_str(exc),
                })

                logs.log_data(
                    f'-- UnExpect Exception in Pinterest Local task_id: {task_id}\n'
                    f'-- Error: {exc}',
                    'error'
                )

            # 컨테이너 최대 수명시간 1시간
            if int(time.time()) > int(container_start_time) + 3600:
                logs.log_data(
                    f"Time Limit: 1 Hours Over",
                    "warning",
                )
                exit()

            loop_count += 1

    exit()
