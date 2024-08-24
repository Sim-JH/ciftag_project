from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from fastapi.responses import FileResponse


from ciftag.web.schemas.pinterest import (
    PinterestResponseBase,
    PinterestCrawlData
)

router = APIRouter()


@router.get("/result", response_model=List[PinterestResponseBase])
async def get_pinterest_result(
    crawl_pk: List[int] = Query(default=[], title="크롤링 요청 ids", description="빈 리스트 일시 전체 조회"),
):
    """핀터레스트 크롤링 결과 조회"""
    pass


@router.get("/img/{result_pk}", response_model=List[PinterestCrawlData])
async def get_pinterest_img(
    pinterest_pk: int = Path(title="핀터레스트 결과 id", description="0입력 시 전체 조회"),
    min_height: Union[str, None] = Query(default=None, title="조회할 이미지 최소 높이"),
    max_height: Union[str, None] = Query(default=None, title="조회할 이미지 최대 높이"),
    min_width: Union[str, None] = Query(default=None, title="조회할 이미지 최소 너비"),
    max_width: Union[str, None] = Query(default=None, title="조회할 이미지 최대 너비"),
):
    """핀터레스트 이미지 목록 조회"""
    pass


@router.get("/thum/{img_pk}",  response_class=FileResponse)
def get_pinterest_thumnail(
    img_pk: int = Path(gt=0, title="핀터레스트 이미지 id", description="download가 True인 이미지만 가능"),
):
    """이미지 썸네일 확인"""
    # TODO download가 성공한 id만 가능
    # return FileResponse(file_path, media_type="image/jpg")
    pass
