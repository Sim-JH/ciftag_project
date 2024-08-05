from celery import Celery
from celery.schedules import crontab

from ciftag.settings import SQL_ALCHEMY_CONN, conf

celery_app = Celery(
    "ciftag",
    broker=conf.get('celery', 'broker'),
    # backend="rpc://",
    backend="db+" + SQL_ALCHEMY_CONN,
    include=[
    ],
)

celery_app.conf.update(
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
