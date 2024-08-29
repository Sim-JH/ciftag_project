
"""
ECS container가 실행 -> 지속적으로 sqs를 pop -> 모든 작업 수행 완료 후 exit_handler로 종료처리
"""
import sys
import time
import random
import json
import atexit
from datetime import datetime

import ciftag.utils.logger as logger
import ciftag.services.pinterest.run as pinterest
from ciftag.settings import SERVER_TYPE, TIMEZONE, env_key
from ciftag.models import enums
from ciftag.utils.converter import get_traceback_str
from ciftag.integrations.sqs import SqsManger
from ciftag.scripts.common import insert_task_status, update_task_status



def exit_handler():
    # if 현재 컨테이너가 실행 중인 ecs 중 마자믹 일 시

    # 외부 작업 로그 update

    # pint info update
    pass


server_type = sys.argv[1]
run_type = sys.argv[2]

# container별 log_name 지정 필요하려나?
# container_ip = check_output(["curl", "https://lumtest.com/myip"])

logs = logger.Logger()
atexit.register(exit_handler)

container_start_time = time.time()

re_call = 0  # get sqs 시도 횟수
loop_count = 0  # 현 컨테이너의 작업 횟수
vpn_log_flag = False

while True:
    time.sleep(random.randrange(1, 3))

    sqs_queue = SqsManger(server_type=SERVER_TYPE)
    data = sqs_queue.get()

    # get sqs 실패 시 n회까지 재시도
    if not data:
        if re_call <= env_key.MAX_RETRY:
            re_call += 1
            logs.log_data(f"SQS Recall: {str(re_call)}")
            time.sleep(10)
        else:
            logs.log_data(f"Not Found SQS")
            break

    else:
        logs.log_data(f"--- Get SQS Datas : {str(data)}")

        body = data.copy()
        body['retry'] = int(data['retry']) + 1
        re_call = 1
        sqs_queue.delete()

        work_id = body['work_id']
        runner_identify = body['runner_identify']
        goal_cnt = body['goal_cnt']

        # 내부 작업 로그 insert
        queue_meta = {
            'work_pk': work_id,
            'runner_identify': runner_identify,
            'body': json.dumps(data, ensure_ascii=False),
            'task_sta': enums.TaskStatusCode.load.name,  # sql 상에선 string으로 들어가야 함
            'get_cnt': 0,
            'goal_cnt': goal_cnt,
            'start_dt': datetime.now(TIMEZONE)
        }

        task_id = insert_task_status(queue_meta)

        if loop_count == 0:
            vpn_log_flag = True  # 한 번이라도 queue 소비한 컨테이너인지 체크

        logs.log_data(f"SQS loop count : {loop_count}")

        try:
            if run_type == "pinterest":
                result = pinterest.run(
                    task_id,
                    work_id,
                    body['pint_id'],
                    body['cred_info'],
                    runner_identify,
                    goal_cnt,
                    data
                )

            # 실패 시 큐 재삽입
            if not result['result'] and result["message"]:
                if result["message"] == "Timeout":
                    # 재시도 대상
                    if int(data["retry"]) < 3:
                        sqs_queue.put(body)
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
                'traceback': get_traceback_str(exc.__traceback__),
            })

            logs.log_data(
                f'-- UnExpect Exception in Pinterest Local task_id: {task_id}',
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
