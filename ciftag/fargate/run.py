
"""
ECS container가 실행 -> 지속적으로 sqs를 pop -> 모든 작업 수행 완료 후 exit_handler로 종료처리
"""
import sys
import time
import random
import atexit
from collections import defaultdict
from subprocess import check_output

from ciftag.settings import SERVER_TYPE
from ciftag.fargate.sqs import SqsManger

import ciftag.utils.logger as logger
import ciftag.services.pinterest.run as pinterest


def exit_handler():
    # if 현재 컨테이너가 실행 중인 ecs 중 마자믹 일 시
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
    time.sleep(random.randrange(5, 11))

    sqs_queue = SqsManger(server_type=SERVER_TYPE)
    data = sqs_queue.get()

    # get sqs 실패 시 5회까지 재시도
    if not data:
        if re_call <= 5:
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

        # TODO try catch 보호 없어도 되나? + 빨리 get한 queue를 지워줘야함
        sqs_queue.delete()

        if loop_count == 0:
            vpn_log_flag = True  # 한 번이라도 queue 소비한 컨테이너인지 체크

        logs.log_data(f"SQS loop count : {loop_count}")

        try:
            if run_type == "pinterest":
                run_result = pinterest.run(data)

        except Exception as e:
            run_result = {"result": False, "message": "Exception Fail"}

        # 실패 시 큐 재삽입
        if not run_result['result'] and run_result["message"] == "Exception Fail":
            if int(data["retry"]) < 3:
                sqs_queue.put(body)
            else:
                logs.log_data(
                    f'--- Retry Over Datas : {str(body)}',
                    'Error'
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
