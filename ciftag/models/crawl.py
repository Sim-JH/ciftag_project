from sqlalchemy import Column,  ForeignKey, Integer, String, Boolean, Enum

from ciftag.models import enums
from ciftag.models.base import Base, TimestampMixin


class CrawlRequestInfo(Base, TimestampMixin):
    """크롤링 요청 정보"""

    __tablename__ = "crawl_req_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    run_on = Column(Enum(enums.RunOnCode))  # 수행한 환경
    target_code = Column(Enum(enums.CrawlTargetCode))  # 대상 사이트 코드
    triggered = Column(Boolean)  # 작업 트리거 됨
    cnt = Column(Integer)  # 목표 이미지 갯수
    etc = Column(String, nullable=True)  # 비고

