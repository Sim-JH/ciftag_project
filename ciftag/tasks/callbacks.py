from typing import Any, Dict

from ciftag.celery_app import app
from ciftag.scripts.common import update_task_status


@app.task(bind=True, name='ciftag.callbacks.pinterest_success')
def task_success_callback(response: Dict[str, Any]):
    task_id = response['task_id']
    pass


@app.task(bind=True, name='ciftag.callbacks.pinterest_fail')
def task_fail_callback(response: Dict[str, Any]):
    task_id = response['task_id']
    pass
