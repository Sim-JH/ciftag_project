from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session


from ciftag.web.schemas.crawl import (
    CrawlRequestBase,
    CrawlResponseBase
)


router = APIRouter()


@router.get("/{crawl_pk}", response_model=List[CrawlResponseBase])
async def get_crawl_list(
    crawl_pk: int = Path(default=0, title="크롤링 요청 id", description="0입력 시 전체 조회"),
    user_pk: Union[int, None] = Query(default=None, title="조회할 사용자 id"),
    cred_pk: Union[int, None] = Query(default=None, title="조회할 인증 id"),
    target_code: Union[str, None] = Query(default=None, title="조회할 크롤링 대상 사이트"),
    result_code: Union[str, None] = Query(default=None, title="조회할 결과 코드"),
    run_on: Union[int, None] = Query(default=None, title="조회할 실행 환경 코드"),
    tags: List[str] = Query(default=[], title="조회할 tag"),
):
    """전체 크롤링 현황 조회"""
    pass


@router.post("/", response_model=int)
def post_crawl_list(
    request: CrawlRequestBase,
    min_height: Union[str, None] = Body(default=None, title="이미지 최소 높이"),
    max_height: Union[str, None] = Body(default=None, title="이미지 최대 높이"),
    min_width: Union[str, None] = Body(default=None, title="이미지 최소 너비"),
    max_width: Union[str, None] = Body(default=None, title="이미지 최대 너비"),
):
    """크롤링 요청"""
    # TODO min_height/max_height/min_width/max_width는 비고로
    # TODO celery 큐 실행만 시킬 예정이므로 동기적으로
    # limit_request(user_pk)  # TODO to many request 구현하기
    pass  # return crawl id


# def limit_request(user_pk: str):
#     # key = f"crawl_request:{user_pk}"
#     # if redis.get(key):
#     #     raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
#     # redis.setex(key, 60, 'true')  # 60초 동안 요청 제한
