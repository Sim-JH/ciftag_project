import os
import zipfile
from io import BytesIO
from typing import List, Union, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, File, UploadFile

from ciftag.configuration import conf
from ciftag.exceptions import CiftagAPIException
from ciftag.web.schemas.download import DownloadRequestBase
from ciftag.web.crud.download import (
    download_image_from_url_service,
    download_image_by_tags_service
)

router = APIRouter()


@router.post("/target/{target_code}", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
def download_image_url(
    request: DownloadRequestBase,
    target_code: str = Path(title="대상 사이트 코드"),
):
    """data id로부터 이미지 download"""
    # TODO 정기 다운로드의 경우 DB에 태그별 다운로드 프리셋을 지정해 해당 방식대로 다운로드
    return download_image_from_url_service(target_code, request)


@router.post("/tags", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
async def download_image_url_by_tags(
    tags: List[str] = Query(title="다운로드 대상 tag"),
    sample_zip: UploadFile = File(
        title="샘플 이미지 파일", description="샘플 이미지를 zip파일 형태로 제공. 일정한 사이즈(오차 10%내외)의 이미지 권장"
    ),
    target_size: Optional[tuple[int, int]] = Query(
        default=None, title="타겟 이미지 사이즈", description="타겟 이미지 사이즈(weight, height)도 제공 샘플 이미지로부터 오차 10% 내외 권장"
    ),
    threshold: float = Query(default=0.8, title="쓰레쉬 홀드", description='목표 정확도 0~1'),
):
    """태그 기반 다운로드. tag + cnn 기반 이미지 필터링 적용"""
    if not sample_zip.filename.endswith(".zip"):
        raise CiftagAPIException(message="Only zip files are allowed.", status_code=400)

    # ZIP 파일을 임시 경로에 저장
    try:
        tmp_dir = f"{conf.get("dir", "data_home")}/Temp"
        os.makedirs(tmp_dir, exist_ok=True)
        zip_path = os.path.join(tmp_dir, sample_zip.filename)

        with open(zip_path, "wb") as f:
            f.write(await sample_zip.read())

    except zipfile.BadZipFile:
        raise CiftagAPIException(message="Invalid zip file.", status_code=400)

    return download_image_by_tags_service(tags, zip_path, target_size, threshold)
