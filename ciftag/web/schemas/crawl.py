from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from ciftag.models import enums


class CrawlBase(BaseModel):
    user_pk: int = Field(None, gt=0, title="사용자 pk")
    target_code: enums.CrawlTargetCode = Field(
        "1",
        title="크롤링 대상 사이트 코드",
        description="크롤링 대상 사이트 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.CrawlTargetCode])
    )  # TODO 추후에는 복수의 target에 대해 요청이 가능하도록
    run_on: enums.RunOnCode = Field(
        "0",
        title="실행 환경 코드",
        description="실행 환경 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.RunOnCode])
    )
    tags: list = Field(None, title="검색 할 태그 목록")
    cnt: int = Field(1, gt=0, lt=100, title="크롤링 할 이미지 갯수", description="최대 100개까지")


class CrawlRequestBase(CrawlBase):
    min_height: int = Field(0, title="이미지 최소 높이")
    max_height: int = Field(0, title="이미지 최대 높이")
    min_width: int = Field(0, title="이미지 최소 너비")
    max_width: int = Field(0, title="이미지 최대 너비")


class CrawlInfoResponseBase(CrawlBase):
    id: int = Field(None, title="인덱스")
    tags: str = Field(None, title="태그 목록")
    created_at: datetime = Field(title="생성 시간")
    updated_at: datetime = Field(title="수정 시간")
    etc: Optional[str] = Field(None, title="비고")  # nullable

    class Config:
        from_attributes = True

