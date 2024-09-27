from datetime import datetime
from typing import Any, Dict

import ciftag.utils.logger as logger
from ciftag.exceptions import CiftagWorkException
from ciftag.celery_app import app


logs = logger.Logger('Celery')


# 미사용으로 변경. 추후 chain 작업 필요시 고려
@app.task(name='ciftag.callbacks.task_success')
def task_success_callback(response: Dict[str, Any]):
    logs.log_data(f'response: {response}')


# on_error
@app.task(name='ciftag.callbacks.task_fail')
def task_fail_callback(request, ext, traceback):
    if isinstance(ext, CiftagWorkException) and hasattr(ext, 'traceback_str'):
        error_trace = ext.traceback_str if ext.traceback_str else traceback
    else:
        error_trace = traceback

    logs.log_data(f"==============================================================================\n"
                  f"--- Task Error: {ext}\n"
                  f"-- Celery Meta: {request.id}/{request.task} Retry: {request.retries} \n"
                  f"-- Traceback \n"
                  f"{error_trace}",
                  'error')
