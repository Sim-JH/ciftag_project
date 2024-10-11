from datetime import time
from typing import Optional
from pydantic import Field

from ciftag.models import enums
from ciftag.web.schemas.common import ImgDataBase
from ciftag.web.schemas.crawl import CrawlInfoResponseBase


class CrawlInfoResponse(CrawlInfoResponseBase):
    work_pk: int = Field(None, title="외부 작업 정보 pk")
    crawl_pk: int = Field(None, title="크롤링 정보 pk")
    cred_pk_list: str = Field(None, title="사용된 인증정보 pk 리스트")
    hits: int = Field(None, title="크롤링 성공 갯수")
    downloads: int = Field(None, title="실제 다운로드한 이미지 갯수")
    elapsed_time: Optional[time] = Field(None, title="크롤링 소모 시간")


class CrawlDataResponse(ImgDataBase):
    id: int = Field(None, title="인덱스")
    pint_pk: int = Field(None, title="핀터레스트 정보 pk")
