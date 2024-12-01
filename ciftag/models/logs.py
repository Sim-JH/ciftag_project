"""작업 로그 관련 된 필드는 외부 키로 사용시 간접적으로만 사용"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.sql import func

from ciftag.settings import TIMEZONE
from ciftag.models import enums
from ciftag.models.base import Base


class WorkInfo(Base):
    """외부 작업 정보"""

    __tablename__ = "work_info"

    id = Column(Integer, primary_key=True)
    work_sta = Column(Enum(enums.WorkStatusCode))  # 외부 작업 상태
    work_type = Column(Enum(enums.WorkTypeCode), default=enums.WorkTypeCode['crawl'])  # 작업 구분 코드
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간


class WorkInfoHistory(Base):
    """외부 작업 정보 이력"""

    __tablename__ = "work_info_hist"

    id = Column(Integer, primary_key=True)
    work_pk = Column(
        Integer,
        ForeignKey("work_info.id")
    )  # 사용자 정보 ID (FK)
    work_sta = Column(Enum(enums.WorkStatusCode))  # 외부 작업 상태
    work_type = Column(Enum(enums.WorkTypeCode), default=enums.WorkTypeCode['crawl'])  # 작업 구분 코드
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE)
    )


class TaskInfo(Base):
    """내부 작업 정보 이력
    요청으로부터 main topic으로 분할된 task 수행 이력
    task마다 1개씩 발행
    """
    
    __tablename__ = "task_info"

    id = Column(Integer, primary_key=True)
    work_pk = Column(Integer)  # 작업 정보 ID (FK)
    runner_identify = Column(String)  # 처리기 식별자
    body = Column(Text)  # body 정보
    task_sta = Column(Enum(enums.TaskStatusCode))  # 작업 상태
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수  
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간


class TaskInfoHist(Base):
    """내부 작업 정보 이력 히스토리"""

    __tablename__ = "task_info_hist"

    id = Column(Integer, primary_key=True)
    task_pk = Column(
        Integer,
        ForeignKey("task_info.id")
    )  # 사용자 정보 ID (FK)
    work_pk = Column(Integer)  # 작업 정보 ID (FK)
    runner_identify = Column(String)  # 현재 처리기 (worker: work_id + celery task id/fargate: host_name + real ip) + time
    task_sta = Column(Enum(enums.TaskStatusCode))  # 작업 상태
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=func.now())  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE)
    )


class SubTaskInfo(Base):
    """서브 작업 정보 이력
    main topic -> sub topic으로 다시 n개로 분할된 sub task 수행 이력
    sub task마다 1개씩 발행
    """

    __tablename__ = "sub_task_info"

    id = Column(Integer, primary_key=True)
    task_pk = Column(Integer)  # 메인 topic 작업 정보 ID (FK)
    runner_identify = Column(String)  # 처리기 식별자
    task_sta = Column(Enum(enums.TaskStatusCode))  # 작업 상태
    body = Column(Text)  # body 정보
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간


class SubTaskInfoHist(Base):
    """서브 작업 정보 이력 히스토리 """

    __tablename__ = "sub_task_info_hist"

    id = Column(Integer, primary_key=True)
    sub_task_pk = Column(
        Integer,
        ForeignKey("sub_task_info.id")
    )  # 세부 정보 ID (FK)
    task_pk = Column(Integer)  # 메인 topic 작업 정보 ID (FK)
    runner_identify = Column(String)  # 처리기 식별자
    task_sta = Column(Enum(enums.TaskStatusCode))  # 작업 상태
    get_cnt = Column(Integer)  # 크롤링 한 이미지 정보 갯수
    goal_cnt = Column(Integer)  # 할당 받은 이미지 정보 갯수
    msg = Column(String, default=None)  # 에러 메시지
    traceback = Column(Text, default=None)  # 추적 로그
    start_dt = Column(DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE))  # 시작 시간
    end_dt = Column(DateTime(timezone=True), nullable=True)  # 종료 시간
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE)
    )
