from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from fastapi.responses import FileResponse

from ciftag.web.schemas.result import (
    CrawlInfoResponse,
    CrawlDataResponse
)
from ciftag.web.crud.result import (
    get_cred_info_service
)

router = APIRouter()


@router.get("/{target_code}/{user_pk}", response_model=List[CrawlInfoResponse])
async def get_target_info(
    target_code: str = Path(title="대상 사이트 코드", description='0 입력 시 전체 조회'),
    user_pk: int = Path(title="사용자 id", description="0 입력 시 전체 조회"),
):
    """타겟별 크롤링 정보 조회"""
    return await get_cred_info_service(target_code, user_pk)


# @router.get("/img/{target_code}/{user_pk}", response_model=List[CrawlDataResponse])
# async def get_result_img(
#     target_code: str = Path(title="대상 사이트 코드", description='0 입력시 전체 조회'),
#     user_pk: int = Path(title="사용자 id", description="0 입력 시 전체 조회"),
#     min_height: Union[str, None] = Query(default=None, title="조회할 이미지 최소 높이"),
#     max_height: Union[str, None] = Query(default=None, title="조회할 이미지 최대 높이"),
#     max_width: Union[str, None] = Query(default=None, title="조회할 이미지 최대 너비"),
# ):
#     """타겟별 수집 목록 조회"""
#     pass
#
