"""작업 로그 관련 된 필드는 외부 키로 사용시 간접적으로만 사용"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.sql import func

from ciftag.settings import TIMEZONE
from ciftag.models.base import Base, TimestampMixin
from ciftag.models.enums import WorkStatusCode, TaskStatusCode


class WorkInfo(Base):
    """외부 작업 정보"""

    __tablename__ = "work_info"

    id = Column(Integer, primary_key=True)
    work_sta = Column(Enum(WorkStatusCode))  # 외부 작업 상태
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True))  # 종료 시간


class WorkInfoHistory(Base, TimestampMixin):
    """외부 작업 정보 이력"""

    __tablename__ = "work_info_hist"

    id = Column(Integer, primary_key=True)
    work_pk = Column(
        Integer,
        ForeignKey("work_info.id")
    )  # 사용자 정보 ID (FK)
    work_sta = Column(Enum(WorkStatusCode))  # 외부 작업 상태
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=func.now())  # 시작 시간
    end_dt = Column(DateTime(timezone=True))  # 종료 시간


class TaskInfo(Base, TimestampMixin):
    """내부 작업 정보 이력
    task는 ecs fargate or celery worker 별로 한 개씩 발행
    queue 번호는 크롤링 목표 이미지에 따라 큐를 나누고 순서대로 번호를 붙인 것
    """
    
    __tablename__ = "task_info"

    id = Column(Integer, primary_key=True)
    work_pk = Column(Integer)  # 작업 정보 ID (FK)
    task_identify = Column(String)  # 현재 작업 컨테이너 (work_id + host_name + real ip + round(time.time() * 1000))
    body = Column(Text)  # queue body 정보
    task_sta = Column(Enum(TaskStatusCode))  # 내부 작업 상태
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수  
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    start_dt = Column(DateTime(timezone=True), default=func.now())  # 시작 시간
    end_dt = Column(DateTime(timezone=True))  # 종료 시간


class TaskInfoHist(Base, TimestampMixin):
    """내부 작업 정보 이력
    task는 ecs fargate or celery worker 별로 한 개씩 발행
    queue 번호는 크롤링 목표 이미지에 따라 큐를 나누고 순서대로 번호를 붙인 것
    """

    __tablename__ = "task_info_hist"

    id = Column(Integer, primary_key=True)
    task_pk = Column(
        Integer,
        ForeignKey("task_pk.id")
    )  # 사용자 정보 ID (FK)
    work_pk = Column(Integer)  # 작업 정보 ID (FK)
    task_identify = Column(String)  # work_queue_ip 로 구성 (work_id + queue 번호 + real ip)
    task_sta = Column(Enum(TaskStatusCode))  # 내부 작업 상태
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=func.now())  # 시작 시간
    end_dt = Column(DateTime(timezone=True))  # 종료 시간

