from typing import Dict, Any

from ciftag.scripts.core import save_sql


def insert_task_status(args: Dict[str, Any]):
    """내부 작업 & 이력 insert"""
    task_sql = f"""INSERT INTO task_info VALUES (work_pk, runner_identify, body, task_sta, get_cnt, goal_cnt) 
                        VALUES(:work_pk, :runner_identify, :body, :task_sta, :get_cnt, :goal_cnt)
                   RETURNING id"""

    _, task_id = save_sql(task_sql, args=args, returning=True)

    task_h_sql = f"""INSERT INTO task_info_hist VALUES (task_pk, work_pk, runner_identify, body, task_sta, get_cnt, goal_cnt) 
                          VALUES(:task_pk, :work_pk, :runner_identify, :body, :task_sta, :get_cnt, :goal_cnt)"""

    args.update({'task_pk': task_id})

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
    task_sql += f" WHERE id = {task_id} RETURNING id"

    save_sql(task_sql, args=args)

    task_h_sql = f"""INSERT INTO task_info_hist VALUES (task_pk, work_pk, runner_identify, body, task_sta, get_cnt, goal_cnt) 
                VALUES(:task_pk, :work_pk, :runner_identify, :body, :task_sta, :get_cnt, :goal_cnt)"""

    args.update({'task_pk': task_id})

    save_sql(task_h_sql, args=args)

    return task_id
