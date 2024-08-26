from sqlalchemy import Column,  ForeignKey, Integer, String, Boolean, Enum

from ciftag.models.base import Base, CrawlInfoDataMixin, enums


class CrawlRequestInfo(Base, CrawlInfoDataMixin):
    """크롤링 요청 정보"""

    __tablename__ = "crawl_req_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    triggered = Column(Boolean)  # 작업 트리거 됨
    target_code = Column(Enum(enums.CrawlTargetCode))  # 대상 사이트 코드
    etc = Column(String, nullable=True)  # 비고

