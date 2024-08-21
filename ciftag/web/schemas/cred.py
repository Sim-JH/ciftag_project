from datetime import datetime
from typing import Optional

from ciftag.models import enums

from pydantic import BaseModel, Field


class CredRequestBase(BaseModel):
    cred_id: str = Field(None, title="인증 ID")
    cred_pw: str = Field(None, title="인증 PW")
    status_code: enums.StatusCode = Field(
        '1',
        title="계정 상태 코드",
        description="계정 상태 코드의 값은 다음과 같습니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.StatusCode])
    )
    target_code: enums.CrawlTargetCode = Field(
        None,
        title="크롤링 대상 사이트 코드",
        description="크롤링 대상 사이트 코드의 값은 다음과 같으며 복수로 가능합니다: "
                    + ", ".join([f"{e.name}: {e.value}" for e in enums.CrawlTargetCode])
    )
    etc: Optional[str] = Field(None, title="기타 정보")


class CredResponseBase(CredRequestBase):
    id: int = Field(None, title="인덱스")
    last_connected_at: Optional[datetime] = Field(None, title="마지막 접속")
