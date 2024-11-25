from __future__ import annotations
from datetime import datetime, timedelta
from pytz import timezone

import pendulum

from airflow import DAG
from airflow.operators.sql import SQLCheckOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.bash import BashOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.utils import dates
from airflow.providers.slack.hooks.slack import SlackHook
from functools import partial

default_args = {"start_date": datetime(2023, 2, 1)}

def send_slack(msg):
    now = datetime.now(timezone('Asia/Seoul'))
    formatted_now = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
    SlackHook(
        slack_conn_id="slack_missing_is_running_conn",
    ).call("chat.postMessage",
    json={"channel":"lunar-sf-pipeline",
    "text":f"[{formatted_now}] {msg}"})
    print(f"{msg}")

def slack_alert_callback(context, msg):
    send_slack(msg)


with DAG(
    "check-gather-fin",
    schedule_interval="*/10 22,23 * * *",
    default_args=default_args,
    max_active_runs=1,
    catchup=False,
) as dag:

    check_1st_extract = SQLCheckOperator(
        task_id="check-1st-extraction-fin",
        sql="""select TIME(CONVERT_TZ(NOW(), 'UTC', 'Asia/Seoul')) >= '07:30:00'
                and DATE_ADD(NOW(), interval - 6 hour) > updatedAT
                from `airflow_db`.`trigger_indicator`
                where `desc` = '1st-extract';        
            """,
        conn_id="forspacelab_backend_conn",
    )

    execute_yog_task = TriggerDagRunOperator(
        task_id="execute-yog-task",
        trigger_dag_id="execute-yog-task",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
        on_execute_callback=partial(slack_alert_callback, msg="요기요 sf task 시작"),
        on_failure_callback=partial(slack_alert_callback, msg="요기요 sf task :firecracker:실패"),
        on_success_callback=partial(slack_alert_callback, msg="요기요 sf task 성공"),
    )

    execute_eat_task = TriggerDagRunOperator(
        task_id="execute-eat-task",
        trigger_dag_id="execute-eat-task",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
        on_execute_callback=partial(slack_alert_callback, msg="쿠팡이츠 sf task 시작"),
        on_failure_callback=partial(slack_alert_callback, msg="쿠팡이츠 sf task :firecracker:실패"),
        on_success_callback=partial(slack_alert_callback, msg="쿠팡이츠 sf task 성공"),
    )

    execute_bae_task = TriggerDagRunOperator(
        task_id="execute-bae-task",
        trigger_dag_id="execute-bae-task",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
        on_execute_callback=partial(slack_alert_callback, msg="배민 sf task 시작"),
        on_failure_callback=partial(slack_alert_callback, msg="배민 sf task :firecracker:실패"),
        on_success_callback=partial(slack_alert_callback, msg="배민 sf task 성공"),
    )

    refresh_shop_on_puree = TriggerDagRunOperator(
        task_id="refresh-shop-on-puree",
        trigger_dag_id="lunar-shop-gathered-for-puree",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
        on_execute_callback=partial(slack_alert_callback, msg="퓨레서버 post 시작"),
        on_failure_callback=partial(slack_alert_callback, msg="퓨레서버 post :firecracker:실패"),
        on_success_callback=partial(slack_alert_callback, msg="퓨레서버 post 성공"),
    )

    insert_1st_extract_triggered = MySqlOperator(
        sql="insert into `airflow_db`.trigger_indicator set `desc`='1st-extract' on duplicate key update updatedAt =NOW()",
        task_id="insert-1st-ext-triggerd",
        mysql_conn_id="forspacelab_backend_conn",
        database="airflow_db",
    )

    (
        check_1st_extract
        >> execute_yog_task
        >> execute_eat_task
        >> execute_bae_task
        >> refresh_shop_on_puree
        >> insert_1st_extract_triggered
    )
