from typing import List, Optional

from pydantic import BaseModel, Field


class DownloadRequestBase(BaseModel):
    data_pk_list: List[int] = Field([], title="데이터 인덱스 리스트", description="빈 리스트 일시 전체")
