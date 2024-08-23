from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session


from ciftag.web.schemas.crawl import (
    CrawlRequestBase,
    CrawlResponseBase
)
from ciftag.web.crud.crawl import (
    add_crawl_info_with_trigger,
    get_crawl_info_with_service
)

router = APIRouter()


@router.get("/{crawl_pk}", response_model=List[CrawlResponseBase])
async def get_crawl_list(
    crawl_pk: int = Path(title="크롤링 요청 id", description="0입력 시 전체 조회"),
    user_pk: Union[int, None] = Query(default=None, title="조회할 사용자 id"),
    target_code: Union[str, None] = Query(default=None, title="조회할 크롤링 대상 사이트"),
    result_code: Union[str, None] = Query(default=None, title="조회할 결과 코드"),
    run_on: Union[int, None] = Query(default=None, title="조회할 실행 환경 코드"),
    tags: List[str] = Query(default=[], title="조회할 tag"),
):
    """전체 크롤링 현황 조회"""
    return get_crawl_info_with_service(crawl_pk, user_pk, target_code, result_code, run_on, tags)


@router.post("/", response_model=int)
async def post_crawl_image(
    request: CrawlRequestBase
):
    """크롤링 요청 (사용자는 해당 사이트에 등록해놓은 id가 있어야 함)"""
    # TODO min_height/max_height/min_width/max_width는 비고로
    # TODO target_codesms 여러개 가능
    # limit_request(user_pk)  # TODO to many request 구현하기
    return add_crawl_info_with_trigger(request)


# def limit_request(user_pk: str):
#     # key = f"crawl_request:{user_pk}"
#     # if redis.get(key):
#     #     raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
#     # redis.setex(key, 60, 'true')  # 60초 동안 요청 제한
