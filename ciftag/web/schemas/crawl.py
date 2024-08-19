import time
from typing import Optional, List

from pydantic import BaseModel, Field

from ciftag.models import enums


class CrawlRequestBase(BaseModel):
    user_pk: int = Field(None, title="사용자 pk")
    cred_pk: int = Field(None, title="인증 정보 pk")
    target_code: enums.CrawlTargetCode = Field(
        "1",
        title="크롤링 대상 사이트 코드",
        description="크롤링 대상 사이트 코드를 선택합니다. 가능한 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.CrawlTargetCode])
    )
    run_on: enums.RunOnCode = Field(None, title="실행 환경 코드")
    tags: list = Field("1", title="검색 할 태그")
    cnt: List[str] = Field(1, gt=0, lt=100, title="크롤링 할 이미지 갯수", description="최대 100개까지")


class CrawlResponseBase(CrawlRequestBase):
    id: int = Field(None, title="인덱스")
    result_code: enums.CrawlStatusCode = Field(None, title="크롤링 결과 코드")
    elapsed_time: time = Field(None, title="크롤링 소모 시간")
    etc: Optional[str] = Field(None, title="비고")  # nullable

    class Config:
        orm_mode = True

