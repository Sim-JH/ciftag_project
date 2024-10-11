from typing import List, Union

from fastapi import APIRouter, Path, Query


from ciftag.web.schemas.crawl import (
    CrawlRequestBase,
    CrawlInfoResponseBase
)
from ciftag.web.crud.crawl import (
    add_crawl_info_with_trigger,
    get_crawl_info_with_service
)

router = APIRouter()


@router.get("/{crawl_pk}", response_model=List[CrawlInfoResponseBase])
async def get_crawl_list(
    crawl_pk: int = Path(title="크롤링 요청 id", description="0입력 시 전체 조회"),
    user_pk: Union[int, None] = Query(default=None, title="조회할 사용자 id"),
    target_code: Union[str, None] = Query(default=None, title="조회할 크롤링 대상 사이트"),
    result_code: Union[str, None] = Query(default=None, title="조회할 결과 코드"),
    run_on: Union[int, None] = Query(default=None, title="조회할 실행 환경 코드"),
    tags: List[str] = Query(default=[], title="조회할 tag"),
):
    """전체 크롤링 요청 현황 조회"""
    return await get_crawl_info_with_service(crawl_pk, user_pk, target_code, result_code, run_on, tags)


@router.post("/", response_model=int)
async def post_crawl_image(
    request: CrawlRequestBase
):
    """크롤링 요청 (사용자는 해당 사이트에 등록해놓은 id가 있어야 함)"""
    # 동일 태그 여러개 사이트에 대한 요청은 API 호출 측에서 분산하여 요청
    # limit_request(user_pk)  # TODO to many request 구현하기
    return await add_crawl_info_with_trigger(request)


# def limit_request(user_pk: str):
#     # key = f"crawl_request:{user_pk}"
#     # if redis.get(key):
#     #     raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
#     # redis.setex(key, 60, 'true')  # 60초 동안 요청 제한
