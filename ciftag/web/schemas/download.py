from pydantic import BaseModel
from typing import List


class DownloadRequestBase(BaseModel):
    data_pk_list: List[int]
