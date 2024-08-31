from sqlalchemy import Column, ForeignKey, Integer, String, Time

from ciftag.models.base import Base, ImgDataImgDataMixin, CrawlInfoDataMixin


class PinterestCrawlInfo(Base, CrawlInfoDataMixin):
    """핀터레스트 크롤링 수행 정보"""

    __tablename__ = "pint_crawl_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    work_pk = Column(Integer)  # 외부 작업 정보 ID (FK)
    crawl_pk = Column(
        Integer,
        ForeignKey("crawl_req_info.id", onupdate="CASCADE")
    )  # 크롤링 정보 ID (FK)
    cred_pk_list = Column(String)  # 사용 가능한 인증 정보 id 리스트 (FK) "id/id/id" 로 구분
    hits = Column(Integer)  # 크롤링 성공 갯수
    downloads = Column(Integer)  # 실제 이미지로 다운로드한 갯수
    elapsed_time = Column(Time, nullable=True)  # 작업 소모 시간
    etc = Column(String, nullable=True)  # 비고


class PinterestCrawlData(Base, ImgDataImgDataMixin):
    """핀터레스트 크롤링 데이터"""

    __tablename__ = "pint_crawl_data"

    id = Column(Integer, primary_key=True)  # 인덱스
    pint_pk = Column(Integer)  # 핀터레스트 정보 ID (FK)
    thumbnail_url = Column(String)
    image_url = Column(String)
    title = Column(String)
    detail_link = Column(String)
