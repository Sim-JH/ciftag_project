from typing import Any, List, Dict, Tuple, Union

from sqlalchemy import column,  asc, desc
from sqlalchemy.dialects.postgresql import insert

from ciftag.models import Base
from ciftag.integrations.database import DBManager
from ciftag.exceptions import CiftagAPIException


dbm = DBManager()


def select_orm(
        model: Base, target='all', order_by: str = 'created_at', order_direction: str = 'asc'
) -> Union[List[Base] | Base | None]:
    """ 모델 조회 쿼리 """
    with dbm.create_session() as session:
        query = session.query(model)

        order_column = getattr(model, order_by)
        if order_direction == 'asc':
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        if target == "all":
            records = query.all()
        elif target == "scalar":
            records = query.scalar()
        else:
            records = query.one()

    return records


def search_orm(
        model: Base,
        key: str,
        value: Any,
        col=None,
        target='all',
        order_by: str = 'created_at',
        order_direction: str = 'asc'
) -> Union[List[Base] | Base | None]:
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

        order_column = getattr(model, order_by)
        if order_direction == 'asc':
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        if target == "all":
            records = query.all()
        elif target == "scalar":
            records = query.scalar()
        else:
            records = query.one()

    return records


def insert_orm(model: Base, body, returning=False) -> Base:
    """모델 key 기반 record update"""
    record = model(**body.dict())

    with dbm.create_session() as session:
        session.add(record)

    if returning:
        return record.id
    else:
        return record


def update_orm(model: Base, key: str, value: Any, body) -> Base:
    """모델 key 기반 record update"""
    table_key = getattr(model, key)

    if not table_key:
        raise CiftagAPIException(f"Resource {key} not found", 404)

    with dbm.create_session() as session:
        record = session.query(model).filter(table_key == value).update(body.dict())

    return record


def delete_orm(model: Base, key: str, value: Any) -> Base:
    """모델 key 기반 record delete"""
    table_key = getattr(model, key)

    if not table_key:
        raise CiftagAPIException(f"Resource {key} not found", 404)

    with dbm.create_session() as session:
        record = session.query(model).filter(table_key == value).delete()

    return record


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
