from typing import Any, Dict

from ciftag.models import WorkInfo, WorkInfoHistory
from ciftag.integrations.database import DBManager


dbm = DBManager()


def insert_work_status(body: Dict[str, Any]):
    """외부 작업 로그 & 이력 insert"""
    work_record = WorkInfo(**body)

    with dbm.create_session() as session:
        session.add(work_record)
        session.flush()
        work_id = work_record.id
        body.update({'work_pk': work_id})
        session.add(WorkInfoHistory(**body))

    return work_id


def update_work_status(work_id: int, body: Dict[str, Any]):
    """외부 작업 로그 update / 이력 insert"""
    with dbm.create_session() as session:
        session.query(WorkInfo).filter(WorkInfo.id == work_id).update(body)
        session.flush()
        body.update({'work_pk': work_id})
        session.add(WorkInfoHistory(**body))

    return work_id
