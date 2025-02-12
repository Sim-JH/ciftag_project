import os
import zipfile
from io import BytesIO
from typing import List, Union, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, File, UploadFile

from ciftag.configuration import conf
from ciftag.exceptions import CiftagAPIException
from ciftag.web.schemas.download import DownloadRequestBase
from ciftag.web.crud.download import (
    # download_image_from_url_service,
    download_image_by_tags_service
)

router = APIRouter()


# @router.post("/target/{target_code}", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
# def download_image_url(
#     request: DownloadRequestBase,
#     target_code: str = Path(title="대상 사이트 코드"),
# ):
#     """data id로부터 이미지 download 및 메타 업데이트"""
#     return download_image_from_url_service(target_code, request)


@router.post("/tags", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
async def download_image_url_by_tags(
    tags: List[str] = Query(title="다운로드 대상 tag"),
    sample_zip: UploadFile = File(
        title="샘플 이미지 파일", description="샘플 이미지를 zip파일 형태로 제공. 일정한 사이즈(오차 10%내외)의 이미지 권장"
    ),
    target_size: Optional[tuple[int, int]] = Query(
        default=None, title="타겟 이미지 사이즈", description="타겟 이미지 사이즈(weight, height)도 제공 샘플 이미지로부터 오차 10% 내외 권장"
    ),
    threshold: float = Query(default=0.9, title="쓰레쉬 홀드", description='목표 정확도 0~1'),
    model_type: str = Query(default='FaceNet', title="사용할 모델", description='ResNet50, FaceNet, SwinTransformer'),
):
    """태그 기반 다운로드.<br><br>

    여러 cnn기반 이미지 필터링 적용\n
    ResNet50: 성능이 좋지 않음\n
    FaceNet: threshold 0.9 이상\n
    SwinTransformer: threshold 0.65~0.7 이상
    """
    if not sample_zip.filename.endswith(".zip"):
        raise CiftagAPIException(message="Only zip files are allowed.", status_code=400)

    # ZIP 파일을 임시 경로에 저장
    try:
        tmp_dir = f"{conf.get("dir", "data_home")}/Temp"
        os.makedirs(tmp_dir, exist_ok=True)

        base_filename, file_extension = os.path.splitext(sample_zip.filename)
        tmp_filename = f"{base_filename}_{model_type}{file_extension}"

        zip_path = os.path.join(tmp_dir, tmp_filename)

        counter = 1
        # 샘플 파일 중복 방지
        while os.path.exists(zip_path):
            tmp_filename = f"{base_filename}_{model_type}_{counter}{file_extension}"
            zip_path = os.path.join(tmp_dir, tmp_filename)
            counter += 1

        with open(zip_path, "wb") as f:
            f.write(await sample_zip.read())

    except zipfile.BadZipFile:
        raise CiftagAPIException(message="Invalid zip file.", status_code=400)

    return download_image_by_tags_service(tags, zip_path, target_size, threshold, model_type)
