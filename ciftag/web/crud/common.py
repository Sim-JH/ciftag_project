from typing import Any, Dict

from ciftag.models import WorkInfo, WorkInfoHistory, ImageMatch
from ciftag.integrations.database import DBManager

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, case, cast, Float, text


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


def upsert_img_match(data_id: int, target_code: str, filter_dict: Dict[str, float]):
    """이미지 매치 테이블 UPSERT. filter_dict 컬럼의 경우는 통과한 threshold 값이 더 클 경우만 업데이트."""

    # 기본 insert 구문
    stmt = insert(ImageMatch).values(
        data_pk=data_id,
        target_code=target_code,
        filter_dict=filter_dict
    )

    filter_case_statements = ImageMatch.filter_dict

    # filter_dict의 각 필터를 순회하며 조건부 업데이트 로직 추가
    for filter_name, new_value in filter_dict.items():
        # 필터 키가 존재하고, 그 값이 현재 값보다 작은지 비교
        existing_value_expr = func.coalesce(
            cast(func.jsonb_extract_path(ImageMatch.filter_dict, text(f"'{filter_name}'")), Float),
            new_value  # 키가 없을 경우 new_value를 기본값으로 사용
        )

        # jsonb_set 함수 사용 (SQL 텍스트로 경로 처리)
        filter_case_statements = func.jsonb_set(
            filter_case_statements,
            text(f"'{{{filter_name}}}'"),  # 단일 경로 단순처리. {a:{d:c}}와 같은 중첩키 경우는 배열로 키값 줘야함
            func.to_jsonb(
                case(
                    (existing_value_expr < new_value, new_value),  # 기존 값이 작을 경우 업데이트
                    else_=existing_value_expr  # 그렇지 않으면 기존 값 유지
                )
            )
        )
    # conflict 처리 및 세션 커밋
    stmt = stmt.on_conflict_do_update(
        index_elements=['data_pk', 'target_code'],
        set_={'filter_dict': filter_case_statements}  # 누적된 filter_dict case 결과로 업데이트
    )

    with dbm.create_session() as session:
        session.execute(stmt)
        session.commit()