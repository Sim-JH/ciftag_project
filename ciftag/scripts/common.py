from typing import Dict, Any
from datetime import datetime

from ciftag.settings import TIMEZONE
import ciftag.utils.logger as logger
from ciftag.scripts.core import select_sql, save_sql

logs = logger.Logger(log_dir='sql')


def check_task_status(work_id):
    """내부 작업 현황 조회"""
    task_sql = f"""SELECT task_sta FROM task_info 
                    WHERE work_pk = {work_id} AND task_sta != 'result' AND task_sta != 'failed'"""

    result = select_sql(task_sql)

    return result


def aggregate_task_result(work_id):
    """내부 작업 결과 합산 [target 별, cnt 합산, elapsed_time 최대 소모 시간]"""
    task_sql = f"""WITH ranked_rows AS (
                        SELECT (body::jsonb -> 'target_code' ->> 'name') AS target, 
                                get_cnt, 
                                start_dt, 
                                end_dt, 
                                end_dt - start_dt AS elapsed_time,
                                SUM(get_cnt) OVER (PARTITION BY (body::jsonb -> 'target_code' ->> 'name')) AS total_cnt,
                                ROW_NUMBER() OVER (
                                    PARTITION BY (body::jsonb -> 'target_code' ->> 'name') 
                                    ORDER BY (end_dt - start_dt) DESC
                                ) AS rn
                        FROM task_info 
                        WHERE work_pk = {work_id} 
                          AND (task_sta = 'result' OR task_sta = 'failed')
                    )
                    SELECT target, total_cnt, elapsed_time
                    FROM ranked_rows
                    WHERE rn = 1;"""

    result = select_sql(task_sql)

    return result


def insert_task_status(args: Dict[str, Any]):
    """내부 작업 & 이력 insert"""
    task_sql = f"""INSERT INTO task_info (work_pk, runner_identify, body, task_sta, get_cnt, goal_cnt, start_dt) 
                        VALUES(:work_pk, :runner_identify, :body, :task_sta, :get_cnt, :goal_cnt, :start_dt)
                   RETURNING id"""

    _, task_id = save_sql(task_sql, args=args, returning='id')

    task_h_sql = f"""INSERT INTO task_info_hist (task_pk, work_pk, runner_identify, task_sta, get_cnt, goal_cnt, start_dt, created_at) 
                          VALUES(:task_pk, :work_pk, :runner_identify, :task_sta, :get_cnt, :goal_cnt, :start_dt, :created_at)"""

    args.update(
        {
            'task_pk': task_id,
            'created_at': datetime.now(TIMEZONE)
        }
    )

    save_sql(task_h_sql, args=args)

    return task_id


def update_task_status(task_id: int, args: Dict[str, Any]):
    """내부 작업 로그 update / 이력 insert"""
    task_sql = "UPDATE task_info SET "

    # args에 있는 키들을 기반으로 SET 절 동적 생성
    set_clauses = []

    for key in args.keys():
        set_clauses.append(f"{key} = :{key}")

    task_sql += ", ".join(set_clauses)

    # 업데이트된 row의 값을 가져오기
    task_sql += f" WHERE id = {task_id} RETURNING *"

    _, task_row = save_sql(task_sql, args=args, returning=True)

    task_row_dict = {
        'task_pk': task_row[0],
        'work_pk': task_row[1],
        'runner_identify': task_row[2],
        'task_sta': task_row[4],
        'get_cnt': task_row[5],
        'goal_cnt': task_row[6],
        'msg': task_row[7],
        'traceback': task_row[8],
        'start_dt': task_row[9],
        'end_dt': task_row[10],
        'created_at': datetime.now(TIMEZONE)
    }

    task_h_sql = f"""INSERT INTO task_info_hist (task_pk, work_pk, runner_identify, task_sta, get_cnt, goal_cnt, msg, traceback, start_dt, end_dt, created_at) 
                          VALUES(:task_pk, :work_pk, :runner_identify, :task_sta, :get_cnt, :goal_cnt, :msg, :traceback, :start_dt, :end_dt, :created_at)"""

    save_sql(task_h_sql, args=task_row_dict)

    return task_id


def insert_sub_task_status(args: Dict[str, Any]):
    """세부 작업 & 이력 insert"""
    task_sql = f"""INSERT INTO sub_task_info (task_pk, runner_identify, task_sta, body, get_cnt, goal_cnt, start_dt) 
                        VALUES(:task_pk, :runner_identify, :task_sta, :body, :get_cnt, :goal_cnt, :start_dt)
                   RETURNING id"""

    _, sub_task_id = save_sql(task_sql, args=args, returning='id')

    task_h_sql = f"""INSERT INTO sub_task_info_hist (sub_task_pk, task_pk, runner_identify, task_sta, get_cnt, goal_cnt, start_dt, created_at) 
                          VALUES(:sub_task_pk, :task_pk, :runner_identify, :task_sta, :get_cnt, :goal_cnt, :start_dt, :created_at)"""

    args.update(
        {
            'task_pk': sub_task_id,
            'created_at': datetime.now(TIMEZONE)
        }
    )

    save_sql(task_h_sql, args=args)

    return sub_task_id


def update_sub_task_status(sub_task_id: int, args: Dict[str, Any]):
    """세부 작업 로그 update / 이력 insert"""
    task_sql = "UPDATE sub_task_info SET "

    # args에 있는 키들을 기반으로 SET 절 동적 생성
    set_clauses = []

    for key in args.keys():
        set_clauses.append(f"{key} = :{key}")

    task_sql += ", ".join(set_clauses)

    # 업데이트된 row의 값을 가져오기
    task_sql += f" WHERE id = {sub_task_id} RETURNING *"

    _, task_row = save_sql(task_sql, args=args, returning=True)

    task_row_dict = {
        'sub_task_id': task_row[0],
        'task_pk': task_row[1],
        'runner_identify': task_row[2],
        'task_sta': task_row[3],
        'get_cnt': task_row[5],
        'goal_cnt': task_row[6],
        'msg': task_row[7],
        'traceback': task_row[8],
        'start_dt': task_row[9],
        'end_dt': task_row[10],
        'created_at': datetime.now(TIMEZONE)
    }

    task_h_sql = f"""INSERT INTO sub_task_info_hist (sub_task_pk, work_pk, task_pk, runner_identify, task_sta, get_cnt, goal_cnt, msg, traceback, start_dt, end_dt, created_at) 
                          VALUES(:sub_task_pk, :work_pk, :task_pk, :runner_identify, :task_sta, :get_cnt, :goal_cnt, :msg, :traceback, :start_dt, :end_dt, :created_at)"""

    save_sql(task_h_sql, args=task_row_dict)

    return sub_task_id