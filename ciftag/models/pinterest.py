from sqlalchemy import Column, ForeignKey, Integer, String, Enum

from ciftag.models.base import Base, TimestampMixin
from ciftag.models.crawl import CrawlRequestInfo
from ciftag.models.enums import RunOnCode


class PinterestCrawlInfo(CrawlRequestInfo):
    """핀터레스트 크롤링 수행 정보"""

    __tablename__ = "pint_crawl_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    crawl_pk = Column(
        Integer,
        ForeignKey("crawl_req_info.id", onupdate="CASCADE"),
    )  # 크롤링 정보 ID (FK)
    hits = Column(Integer)  # 크롤링 성공 갯수
    etc = Column(String, nullable=True)


class PinterestCrawlData(Base, TimestampMixin):
    """핀터레스트 크롤링 데이터"""

    __tablename__ = "pint_crawl_data"

    id = Column(Integer, primary_key=True)  # 인덱스
    pint_pk = Column(
        Integer,
        ForeignKey("pint_crawl_info.id", onupdate="CASCADE"),
    )  # 핀터레스트 정보 ID (FK)
    run_on = Column(Enum(RunOnCode))  # 수행한 환경
    min_width = Column(Integer)  # 이미지 최소 너비
    max_width = Column(Integer)  # 이미지 최대 너비
    path = Column(String)  # 이미지 경로
    size = Column(String)  # 압축 파일 사이즈 (Byte)
