from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from fastapi.responses import FileResponse

from ciftag.web.schemas.result import (
    CrawlInfoResponse,
    CrawlDataResponse
)
from ciftag.web.crud.result import (
    get_target_crawl_info_service,
    get_target_crawl_data_service
)

router = APIRouter()


@router.get("/{target_code}/{user_pk}", response_model=List[CrawlInfoResponse])
async def get_target_crawl_info(
    target_code: str = Path(title="대상 사이트 코드", description='0 입력 시 전체 조회'),
    user_pk: int = Path(title="사용자 id", description="0 입력 시 전체 조회"),
):
    """타겟별 크롤링 정보 조회"""
    return await get_target_crawl_info_service(target_code, user_pk)


@router.get("/img/{target_code}/{user_pk}", response_model=List[CrawlDataResponse])
async def get_result_img(
    target_code: str = Path(title="대상 사이트 코드", description='0 입력시 전체 조회'),
    user_pk: int = Path(title="사용자 id", description="0 입력 시 전체 조회"),
    min_height: Optional[str] = Query(default=None, title="조회할 이미지 최소 높이"),
    max_height: Optional[str] = Query(default=None, title="조회할 이미지 최대 높이"),
    min_width: Optional[str] = Query(default=None, title="조회할 이미지 최소 너비"),
    max_width: Optional[str] = Query(default=None, title="조회할 이미지 최대 너비"),
):
    """타겟별 수집 목록 조회"""
    return await get_target_crawl_data_service(
        target_code,
        user_pk,
        min_height,
        max_height,
        min_width,
        max_width
    )

