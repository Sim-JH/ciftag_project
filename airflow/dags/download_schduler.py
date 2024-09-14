import json
from datetime import datetime

from airflow import DAG
from airflow.timetables.trigger import CronTriggerTimetable
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator

# 기본 설정
default_args = {"start_date": datetime(2024, 9, 5)}


def process_and_send_requests(ti):
    # 각 target_code 별로 api server request
    result = ti.xcom_pull(task_ids='get_crawl_list')
    if not result:
        raise ValueError("크롤링 목록이 없습니다.")

    for row in result:
        target_code = row[0]
        data_pk_list = row[1]

        # POST 요청을 보내기 위한 HTTP Operator
        send_task = SimpleHttpOperator(
            task_id=f'send_request_for_{target_code}',
            http_conn_id='main_dev_server_connection',
            endpoint=f'/api/schedule/{target_code}',
            method='POST',
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "data_pk_list": data_pk_list
            }),
            log_response=True
        )

        # 태스크 실행
        send_task.execute(ti.get_template_context())


with DAG(
    "downlad_schduler",
    timetable=CronTriggerTimetable('0 16 * * *', timezone='Asia/Seoul'),
    default_args=default_args,
    max_active_runs=1,
    catchup=False,
) as dag:
    # 어제자 target 별 크롤링 데이터 목록
    get_crawl_list = PostgresOperator(
        task_id='get_crawl_list',
        postgres_conn_id='main_postgresql_dev_connection',
        sql="""SELECT 
                    enum_table.enumsortorder::INTEGER AS target_code,
                    array_agg(p_data.id) AS p_data_ids
                 FROM public.crawl_req_info AS req
                 JOIN public.pint_crawl_info AS p_info ON req.id = p_info.crawl_pk
                 JOIN public.pint_crawl_data AS p_data ON p_info.id = p_data.pint_pk
                 JOIN (
                         SELECT e.enumlabel, e.enumsortorder
                         FROM pg_enum e
                         JOIN pg_type t ON e.enumtypid = t.oid
                         WHERE t.typname = 'crawltargetcode'
                     ) AS enum_table ON enum_table.enumlabel::TEXT = req.target_code::TEXT
                 WHERE p_data.download = FALSE
                   AND req.created_at::date BETWEEN CURRENT_DATE - INTERVAL '1 day' AND CURRENT_DATE
                 GROUP BY target_code_value
                 ORDER BY target_code_value;""",
    )

    # 각 target_code에 대해 동적으로 HTTP 요청 (조회 되는 id양 증가 시 airflow는 target_code까지만 조회하고 id처리는 api상에서 이뤄지도록)
    send_requests = PythonOperator(
        task_id='process_and_send_requests',
        python_callable=process_and_send_requests
    )

    get_crawl_list >> send_requests
