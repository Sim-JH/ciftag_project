from datetime import datetime
from typing import Any, Dict

import ciftag.utils.logger as logger
from ciftag.utils.converter import get_traceback_str
from ciftag.celery_app import app


logs = logger.Logger('callback')


# 미사용으로 변경. 추후 chain 작업 필요시 고려
@app.task(name='ciftag.callbacks.pinterest_success')
def task_success_callback(response: Dict[str, Any]):
    logs.log_data(f'response: {response}')


# on_error
@app.task(name='ciftag.callbacks.pinterest_fail')
def task_fail_callback(request, ext, traceback):
    logs.log_data(f"=======================================================================\n"
                  f"--- Task Error: {ext}\n"
                  f"-- Celery Meta: {request.id}/{request.task} Retry: {request.retries} \n"
                  f"-- Traceback \n"
                  f"{get_traceback_str(traceback)}")
