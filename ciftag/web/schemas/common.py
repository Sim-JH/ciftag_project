from pydantic import BaseModel, Field

from ciftag.models import enums


class ImgDataBase(BaseModel):
    run_on: enums.RunOnCode = Field(None, title="수행한 환경")
    height: int = Field(None, title="이미지 높이")
    width: int = Field(None, title="이미지 너비")
    thum_path: str = Field(None, title="썸네일 경로")
    img_path: str = Field(None, title="이미지 경로")
    size: str = Field(None, title="압축 파일 사이즈 (Byte)")
    download: bool = Field(False, title="실제 다운로드 여부")

    class Config:
        orm_mode = True
