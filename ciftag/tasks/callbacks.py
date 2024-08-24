from datetime import datetime
from typing import Any, Dict

import ciftag.utils.logger as logger
from ciftag.settings import TIMEZONE
from ciftag.celery_app import app
from ciftag.models import enums
from ciftag.scripts.common import update_task_status


logs = logger.Logger('celery')


@app.task(name='ciftag.callbacks.pinterest_success')
def task_success_callback(response: Dict[str, Any]):
    logs.log_data(f'response: {response}')
    # task_id = response['task_id']
    # get_cnt = response['get_cnt']
    #
    # update_task_status(task_id, {
    #     'task_sta': enums.TaskStatusCode.success.name,
    #     'get_cnt': get_cnt,
    #     'end_dt': datetime.now(TIMEZONE)
    # })
    #

@app.task(name='ciftag.callbacks.pinterest_fail')
def task_fail_callback(request, ext, traceback):
    logs.log_data(f'ext: {ext}')
    logs.log_data(f'traceback: {traceback}')
    # task_id = request.kwargs.get('task_id')
    # get_cnt = request.kwargs.get('get_cnt')
    #
    # update_task_status(task_id, {
    #     'task_sta': enums.TaskStatusCode.failed.name,
    #     'get_cnt': get_cnt,
    #     'msg': str(ext),
    #     'traceback': traceback,
    #     'end_dt': datetime.now(TIMEZONE)
    # })
