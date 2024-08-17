from sqlalchemy import Column,  ForeignKey, Integer, String, Enum, Time

from ciftag.models.base import Base, TimestampMixin
from ciftag.models.enums import RunOnCode, CrawlTargetCode, CrawlResultCode


class CrawlRequestInfo(Base, TimestampMixin):
    """크롤링 요청 정보"""

    __tablename__ = "crawl_req_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    cred_pk = Column(
        Integer,
        ForeignKey("cred_info.id", onupdate="CASCADE"),
    )  # 인증 정보 ID (FK)
    target_code = Column(Enum(CrawlTargetCode))  # 대상 사이트 코드
    result_code = Column(Enum(CrawlResultCode))  # 수행 결과 코드
    run_on = Column(Enum(RunOnCode))  # 수행한 환경
    tags = Column(String)  # 크롤링 대상 태그 "tag/tag/tag" 로 구분
    cnt = Column(Integer)  # 목표 이미지 갯수
    elapsed_time = Column(Time, nullable=False)  # 작업 소모 시간
    etc = Column(String, nullable=True)  # 비고
