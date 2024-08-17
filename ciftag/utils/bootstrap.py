from sqlalchemy import inspect

import ciftag.utils.logger as logger
from ciftag.settings import engine
from ciftag.models import Base

logs = logger.Logger()


def initdb(debug=False):
    """초기 테이블 세팅 (중복 시 x)"""
    logs.log_data('Init all tables')

    # 새로 생성하는 테이블 목록 출력 할 시
    if debug:
        # 현재 존재하는 테이블 리스트
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # 생성할 테이블들 리스트
        tables_to_create = Base.metadata.tables.keys()
        tables_to_be_created = [table_name for table_name in tables_to_create if table_name not in existing_tables]

        logs.log_data(f"Tables to be created: {tables_to_be_created}")

    Base.metadata.create_all(engine)

    # 그 외 초기 데이터 추가 필요 시
