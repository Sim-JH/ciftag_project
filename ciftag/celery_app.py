from celery import Celery
from celery.schedules import crontab

from ciftag.settings import SQL_ALCHEMY_CONN, env_key

app = Celery(
    "ciftag",
    broker=f"redis://{env_key.REDIS_HOST}:{env_key.REDIS_PORT}/0",
    # backend="rpc://",
    backend="db+" + SQL_ALCHEMY_CONN,
    broker_connection_retry_on_startup=True,  # 시작시 브로커 연결 재시도 제어 여부
    include=[
        "ciftag.tasks.pinterest",
        "ciftag.tasks.callbacks"
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=['json'],
    result_serializer="json",
    task_track_started=True,
    result_extended=True,
    worker_max_tasks_per_child=1
)

# celery_app.conf.beat_schedule = {
#     "everyhour-task": {
#         "task": "ciftag.schedule.work_beat",
#         "schedule": crontab(minute='*')
#     },
# }
