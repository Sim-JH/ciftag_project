import os
import atexit
import logging
from typing import Optional

import boto3
import pendulum
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.session import Session as SASession

from ciftag.configuration import CIFTAG_HOME, CIFTAG_CONFIG, conf
from ciftag.exceptions import CIFTAGException

TIMEZONE = pendulum.timezone('UTC')

SQL_ALCHEMY_CONN: Optional[str] = ""
RUN_ON: Optional[str] = ""

engine: Optional[Engine] = None
Session: Optional[SASession] = None


def tz_converter(*args):
    return pendulum.now(TIMEZONE).timetuple()


def configure_vars():
    global SQL_ALCHEMY_CONN
    global RUN_ON
    global TIMEZONE

    RUN_ON = os.environ['RUN_ON']  # 해당 환경변수가 없다면 에러 대상
    SQL_ALCHEMY_CONN = conf.get('core', 'sql_alchemy_conn')

    tz = conf.get('core', 'default_timezone')  # 한국 시 설정

    if tz == "system":
        TIMEZONE = pendulum.local_timezone()
    else:
        TIMEZONE = pendulum.timezone(tz)


def configure_env_from_ps(name='ciftag'):
    client = boto3.client(
        "ssm",
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name="ap-northeast-2"
    )

    parameter = client.get_parameter(Name=f'/{name}', WithDecryption=True)["Parameter"]["Value"]

    for param in parameter.splitlines():
        p = param.split("=", 1)
        if len(p) == 2:
            if p[1][0] == '[' and p[1][-1] == ']':
                os.environ[p[0]] = p[1]
            else:
                os.environ[p[0]] = p[1].replace('"', '')


def configure_orm():
    logging.info('Setting up DB connection pool (PID %s)' % os.getpid())
    global engine
    global Session

    engine = create_engine(SQL_ALCHEMY_CONN, pool_size=10, max_overflow=10, pool_pre_ping=True, pool_recycle=300)
    Session = scoped_session(
        sessionmaker(
            autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
        )
    )


def dispose_orm():
    logging.info('Disposing DB connection pool (PID %s)', os.getpid())
    global engine
    global Session

    if Session:
        Session.remove()
        Session = None
    if engine:
        engine.dispose()
        engine = None


def initialize():
    # local/cloud 환경에 따른 env 세팅
    try:
        from ciftag.utils import logger
        # configure setting
        print('set initialize')
        CIFTAG_HOME.mkdir(parents=True, exist_ok=True)
        conf.read(CIFTAG_CONFIG)
        configure_vars()

        # local은 .env / aws는 파라미터 스토어
        if RUN_ON == "local":
            base_dir = os.path.dirname(__file__)
            module_env_path = os.path.join(base_dir, "module/.env")
            load_dotenv(module_env_path)
        else:
            configure_env_from_ps('ciftag')

        # setup logger
        configure_orm()

        # terminated 시 orm dispose
        atexit.register(dispose_orm)

    except Exception:
        raise CIFTAGException('Fail on initialize')
