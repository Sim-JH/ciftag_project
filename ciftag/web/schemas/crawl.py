from datetime import time
from typing import Optional, List

from pydantic import BaseModel, Field

from ciftag.models import enums


class CrawlBase(BaseModel):
    user_pk: int = Field(None, title="사용자 pk")
    cred_pk: int = Field(None, title="인증 정보 pk")
    target_code: List[enums.CrawlTargetCode] = Field(
        "1",
        title="크롤링 대상 사이트 코드",
        description="크롤링 대상 사이트 코드의 값은 다음과 같으며 복수로 가능합니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.CrawlTargetCode])
    )
    run_on: enums.RunOnCode = Field(
        None,
        title="실행 환경 코드",
        description="실행 환경 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.RunOnCode])
    )
    tags: list = Field("1", title="검색 할 태그")
    cnt: int = Field(1, gt=0, lt=100, title="크롤링 할 이미지 갯수", description="최대 100개까지")


class CrawlRequestBase(CrawlBase):
    min_height: Optional[int] = Field(None, title="이미지 최소 높이")  # nullable
    max_height: Optional[int] = Field(None, title="이미지 최대 높이")  # nullable
    min_width: Optional[int] = Field(None, title="이미지 최소 너비")  # nullable
    max_width: Optional[int] = Field(None, title="이미지 최대 너비")  # nullable


class CrawlResponseBase(CrawlBase):
    id: int = Field(None, title="인덱스")
    result_code: enums.CrawlStatusCode = Field(
        None,
        title="크롤링 결과 코드",
        description="크롤링 결과 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.CrawlStatusCode])
    )
    elapsed_time: time = Field(None, title="크롤링 소모 시간")
    etc: Optional[str] = Field(None, title="비고")  # nullable

    class Config:
        orm_mode = True

