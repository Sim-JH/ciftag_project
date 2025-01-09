import os
from typing import List, Union, Optional

from fastapi import APIRouter, Path, Query, BackgroundTasks, Response
from fastapi.responses import FileResponse

from ciftag.exceptions import CiftagAPIException
from ciftag.utils.apis import remove_file
from ciftag.web.crud.provider import provide_face_crop_image_service

router = APIRouter()


# 다운로드가 완료된 이미지들을 특정 작업 수행 후, 집파일로 압축하여 제공
@router.post("/face/{target_code}", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
async def provide_face_crop_image(
    background_tasks: BackgroundTasks,
    target_code: str = Path(title="대상 사이트 코드"),
    start_idx: Optional[int] = Query(default=None, gt=0, description="해당 번호 이상의 이미지를 대상 최대 +100"),
    end_idx: Optional[int] = Query(default=None, description="해당 번호 이하의 이미지를 대상 최대 -100"),
    resize: Optional[int] = Query(default=None, description="이미지를 리사이즈하여 제공"),
):
    """제공 된 인덱스 범위 내에서 다운로드가 완료 된 이미지의 얼굴 부분을 정사각형으로 crop하여 제공"""
    if start_idx and not end_idx:
        end_idx = start_idx + 100
    elif end_idx and not start_idx:
        start_idx = max(0, end_idx - 100)
    elif not start_idx and not end_idx:
        raise CiftagAPIException(message="Please Input One Of Idx", status_code=400)

    if start_idx > end_idx:
        raise CiftagAPIException(message="Please Input Correct Idx", status_code=400)

    zip_path, crop_file_cnt = provide_face_crop_image_service(target_code, start_idx, end_idx, resize)

    # 응답 후 zip 파일을 삭제하도록 백그라운드 작업 추가
    background_tasks.add_task(remove_file, zip_path)

    # 파일 스트리밍하여 반환
    return FileResponse(path=zip_path, filename=os.path.basename(zip_path), media_type='application/zip')
