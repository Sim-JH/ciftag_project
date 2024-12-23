from sqlalchemy import inspect, create_engine

import ciftag.utils.logger as logger
from ciftag.settings import SERVER_TYPE, configure_env_from_ps, engine
from ciftag.models import Base
from ciftag.scripts.core import save_sql

logs = logger.Logger()


def initdb(aws=False, debug=False):
    """초기 테이블 세팅 aws True일 시 aws rds 초기화 (중복 시 x)"""
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

    # 테이블 생성
    if aws:
        key_body = configure_env_from_ps(
            just_param={
                'DB_USERNAME': '',
                'DB_PASSWORD': '',
                'DB_HOST': '',
                'DB_PORT': '',
            }
        )

        url = f"postgresql://{key_body['DB_USERNAME']}:{key_body['DB_PASSWORD']}@{key_body['DB_HOST']}:{key_body['DB_PORT']}/{SERVER_TYPE}",
        aws_engine = create_engine(
            url,
            pool_size=10,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300
        )

        logs.log_data(f'Cunnecting to {key_body['DB_HOST']}:{key_body['DB_PORT']}')
        Base.metadata.create_all(aws_engine)
    else:
        logs.log_data(f'Cunnecting to {engine.url}')
        Base.metadata.create_all(engine)

    # 그 외 초기 데이터 추가 필요 시
    create_base_account()  # admin/test 없을 시 생성 (index 0/1번)


def create_base_account():
    sql = f"""INSERT INTO user_info (user_ident, user_pw, user_name, auth_code, status_code)
                   SELECT 'admin', 'admin', '관리자', 'admin', 'active'
              WHERE NOT EXISTS (SELECT 1 FROM user_info);"""

    save_sql(sql)

    sql = f"""INSERT INTO user_info (user_ident, user_pw, user_name, auth_code, status_code)
                   SELECT 'test', 'test', '테스트_유저', 'user', 'active'
              WHERE (SELECT COUNT(*) FROM user_info) = 1;"""

    save_sql(sql)
