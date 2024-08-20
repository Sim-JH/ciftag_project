from sqlalchemy import Column, ForeignKey, Integer, String, Enum

from ciftag.models.base import Base, TimestampMixin, ImgDataImgDataMixin
from ciftag.models.crawl import CrawlRequestInfo


class PinterestCrawlInfo(CrawlRequestInfo):
    """핀터레스트 크롤링 수행 정보"""

    __tablename__ = "pint_crawl_info"

    crawl_pk = Column(
        Integer,
        ForeignKey("crawl_req_info.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )  # 크롤링 정보 ID (FK)
    hits = Column(Integer)  # 크롤링 성공 갯수
    downloads = Column(Integer)  # 실제 이미지로 다운로드한 갯수


class PinterestCrawlData(ImgDataImgDataMixin):
    """핀터레스트 크롤링 데이터"""

    __tablename__ = "pint_crawl_data"

    id = Column(Integer, primary_key=True)  # 인덱스
    pint_pk = Column(
        Integer,
        ForeignKey("pint_crawl_info.id", onupdate="CASCADE"),
    )  # 핀터레스트 정보 ID (FK)
