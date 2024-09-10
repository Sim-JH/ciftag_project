from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {"start_date": datetime(2024, 9, 5)}


def generate_pint_update_sql_task(**kwargs):
    # 파라미터 파싱
    conf = kwargs.get('dag_run').conf

    if conf is None:
        raise Exception(r"Can't Parse Parameter")

    work_id = conf.get('work_id')
    pint_id = conf.get('pint_id')
    hits = conf.get('hits')
    elapsed_time = float(conf.get('elapsed_time'))

    # SQL 쿼리 생성
    query = f"""UPDATE pint_crawl_info SET hits='{hits}', elapsed_time='{timedelta(seconds=elapsed_time)}' WHERE id='{pint_id}';"""

    # 파일 경로를 XCom으로 반환
    return {'query': query, 'work_id': work_id}


with DAG(
    "run-after-pinterest",
    schedule_interval=None,
    default_args=default_args,
    max_active_runs=3,
    catchup=False,
) as dag:
    # 인자 파싱 및 sql 생성
    generate_pint_update_sql_task = PythonOperator(
        task_id='generate_pint_update_sql_task',
        python_callable=generate_pint_update_sql_task,
    )

    # pint_info 업데이트
    update_pint_info = PostgresOperator(
        task_id='update_pint_info',
        postgres_conn_id='main_postgresql_dev_connection',
        sql="""{{ ti.xcom_pull(task_ids='generate_pint_update_sql_task')['query'] }}"""
    )

    # pint_info 업데이트
    update_work_info = PostgresOperator(
        task_id='update_work_info',
        postgres_conn_id='main_postgresql_dev_connection',
        sql="""UPDATE work_info SET work_sta='success', end_dt=NOW() 
               WHERE id='{{ ti.xcom_pull(task_ids='generate_pint_update_sql_task')['work_id'] }}';""",
    )

    (generate_pint_update_sql_task >> update_pint_info >> update_work_info)
