from datetime import time
from pydantic import Field

from ciftag.models import enums
from ciftag.web.schemas.common import ImgDataBase
from ciftag.web.schemas.crawl import CrawlResponseBase


class PinterestResponseBase(CrawlResponseBase):
    crawl_pk: int = Field(None, title="크롤링 정보 pk")
    result_code: enums.WorkStatusCode = Field(
        None,
        title="작업 상태 코드",
        description="작업 상태 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.WorkStatusCode])
    )
    tags: str = Field(None, title="검색 할 태그")
    hits: int = Field(None, title="크롤링 성공 갯수")
    downloads: int = Field(None, title="실제 다운로드한 이미지 갯수")
    elapsed_time: time = Field(None, title="크롤링 소모 시간")


class PinterestCrawlData(ImgDataBase):
    id: int = Field(None, title="인덱스")
    pint_pk: int = Field(None, title="핀터레스트 정보 pk")
