from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Path, Query

from ciftag.models import enums
from ciftag.utils.apis import limit_request
from ciftag.web.schemas.crawl import (
    CrawlRequestBase,
    CrawlInfoResponseBase
)
from ciftag.web.crud.crawl import (
    add_crawl_info_with_trigger,
    get_crawl_req_service
)

router = APIRouter()


@router.get("/{crawl_pk}", response_model=List[CrawlInfoResponseBase])
async def get_crawl_request_list(
    crawl_pk: int = Path(title="크롤링 요청 id", description="0입력 시 전체 조회"),
    user_pk: Optional[int] = Query(default=None, title="조회할 사용자 id"),
    target_code: Optional[enums.CrawlTargetCode] = Query(default=None, title="조회할 크롤링 대상 사이트"),
    run_on: Optional[enums.RunOnCode] = Query(default=None, title="조회할 실행 환경 코드"),
    start_time: Optional[datetime] = Query(default=None, title="조회 시작 시간"),
    end_time: Optional[datetime] = Query(default=None, title="조회 종료 시간"),
    tags: List[str] = Query(default=[], title="조회할 tag"),
):
    """전체 크롤링 요청 현황 조회"""
    return await get_crawl_req_service(crawl_pk, user_pk, target_code, run_on, start_time, end_time, tags)


@router.post("/", response_model=int)
async def post_crawl_image(
    request: CrawlRequestBase
):
    """크롤링 요청 (사용자는 해당 사이트에 등록해놓은 id가 있어야 함)"""
    # 동일 태그 여러개 사이트에 대한 요청은 API 호출 측에서 분산하여 요청
    data = request.dict()
    user_pk = data['user_pk']
    limit_request(user_pk)
    return await add_crawl_info_with_trigger(data)

