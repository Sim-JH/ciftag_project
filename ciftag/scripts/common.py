from typing import Dict, Any

from ciftag.scripts.core import save_sql


def insert_task_status(args: Dict[str: Any]):
    task_sql = f"""INSERT INTO task_info VALUES (work_pk, task_identify, body, task_sta, get_cnt, goal_cnt) 
                        VALUES(:work_pk, :task_identify, :body, :task_sta, :get_cnt, :goal_cnt)
                   RETURNING id"""

    _, task_id = save_sql(task_sql, args=args, returning=True)

    task_h_sql = f"""INSERT INTO task_info_hist VALUES (task_pk, work_pk, task_identify, body, task_sta, get_cnt, goal_cnt) 
                          VALUES(:task_pk, :work_pk, :task_identify, :body, :task_sta, :get_cnt, :goal_cnt)"""

    args.update({'task_pk': task_id})

    save_sql(task_h_sql, args=args)

    return task_id


def update_task_status(task_id: int, args: Dict[str: Any]):
    task_sql = f"""UPDATE task_info 
                      SET work_pk = :work_pk,
                          task_identify = :task_identify,
                          body = :body,
                          task_sta = :task_sta,
                          get_cnt = :get_cnt,
                          goal_cnt = :goal_cnt
                   WHERE id = :id
                   RETURNING id"""

    _, task_id = save_sql(task_sql, args=args, returning=True)

    task_h_sql = f"""INSERT INTO task_info_hist VALUES (task_pk, work_pk, task_identify, body, task_sta, get_cnt, goal_cnt) 
                VALUES(:task_pk, :work_pk, :task_identify, :body, :task_sta, :get_cnt, :goal_cnt)"""

    args.update({'task_pk': task_id})

    save_sql(task_h_sql, args=args)

    return task_id
