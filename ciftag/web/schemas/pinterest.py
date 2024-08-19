from pydantic import Field

from ciftag.web.schemas.common import ImgDataBase
from ciftag.web.schemas.crawl import CrawlResponseBase


class PinterestResponseBase(CrawlResponseBase):
    crawl_pk: int = Field(None, title="크롤링 정보 pk")
    hits: int = Field(None, title="크롤링 성공 갯수")
    downloads: int = Field(None, title="실제 다운로드한 이미지 갯수")


class PinterestCrawlData(ImgDataBase):
    id: int = Field(None, title="인덱스")
    pint_pk: int = Field(None, title="핀터레스트 정보 pk")
