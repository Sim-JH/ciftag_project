from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body

from ciftag.web.crud.schedule import (
    download_image_urls,
)

router = APIRouter()


@router.post("/{target_code}", response_model=int, responses={200: {"description": "다운로드 대상 이미지 갯수"}})
def download_image_url(
    target_code: str = Path(title="대상 사이트 코드"),
    data_pk_list: List[int] = Query(default=[], title="크롤링 대상 pk list"),
):
    """data id로부터 이미지 download"""
    return download_image_urls(target_code, data_pk_list)


