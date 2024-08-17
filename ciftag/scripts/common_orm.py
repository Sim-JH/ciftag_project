from typing import Any, List, Dict, Tuple

from sqlalchemy import column
from sqlalchemy.dialects.postgresql import insert

from ciftag.models import Base
from ciftag.integrations.database import DBManager
from ciftag.exceptions import CiftagAPIException


dbm = DBManager()


def select_orm(model: Base, target='all') -> List[Base]:
    """ 모델 조회 쿼리 """
    with dbm.create_session() as session:
        query = session.query(model)

        if target == "all":
            records = query.all()
        elif target == "scalar":
            records = query.scalar()
        else:
            records = query.one()

    return records


def search_orm(model: Base, key: str, value: Any, col=None, target='all') -> List[Base]:
    """모델 key 기반 검색"""
    table_key = getattr(model, key)

    if not table_key:
        raise CiftagAPIException(f"Resource {key} not found", 404)

    with dbm.create_session() as session:
        query = session.query(
            getattr(model, col) if col is not None else model
        ).filter(
            table_key == value
        )

        if target == "all":
            records = query.all()
        elif target == "scalar":
            records = query.scalar()
        else:
            records = query.one()

    return records


def put_orm(model: Base, key: str, value: Any, body) -> List[Base]:
    """모델 key 기반 record update"""
    table_key = getattr(model, key)

    if not table_key:
        raise CiftagAPIException(f"Resource {key} not found", 404)

    with dbm.create_session() as session:
        records = (
            session.query(model).filter(table_key == value).update(body)
        )

    return records


def delete_orm(model: Base, key: str, value: Any) -> List[Base]:
    """모델 key 기반 record delete"""
    table_key = getattr(model, key)

    if not table_key:
        raise CiftagAPIException(f"Resource {key} not found", 404)

    with dbm.create_session() as session:
        records = (
            session.query(model).filter(table_key == value).delete()
        )

    return records


def upsert_orm(model: Base, data_set: Dict[str, Any], constraint: Any, returning=None) -> Tuple[int, bool]:
    """ 모델 기반 record upsert
    insert 됐으면 True, upsert 됐으면 False를 포함하여 반환
    return : list[model id, bool(insert:True/update:False)]
    """
    stmt = insert(model).values(**data_set)

    params = {
        "set_": dict(**data_set)
    }

    if isinstance(constraint, str):
        params.update(constraint=constraint)
    else:
        params.update(index_elements=[constraint])

    with dbm.create_session() as session:
        stmt = stmt.on_conflict_do_update(
            **params
        ).returning(
            model.id if returning is None else returning,
            (column('xmax') == 0).label("inserted")
        )
        returning_ = session.execute(stmt)

    return returning_.fetchall().pop()
