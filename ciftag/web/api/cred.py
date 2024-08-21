from typing import List, Union

from fastapi import APIRouter, Path

from ciftag.models import enums
from ciftag.web.schemas.cred import (
    CredRequestBase,
    CredResponseBase
)
from ciftag.web.crud.cred import (
    get_cred_info_service,
    add_cred_info_service,
    put_cred_info_service,
    delete_cred_info_service
)


router = APIRouter()


@router.get("/{user_pk}", response_model=List[CredResponseBase])
async def get_cred_list(
    user_pk: int = Path(title="사용자 id", description="0입력 시 전체 조회"),
):
    """인증 정보 가져오기"""
    return get_cred_info_service(user_pk)


@router.post("/", response_model=int, responses={200: {"description": "생성된 인증 정보의 고유 식별자(ID)"}})
def post_cred_info(
    request: CredRequestBase,
):
    """인증 정보 생성"""
    return add_cred_info_service(request)


@router.put("/{user_pk}/{cred_pk}", response_model=bool, responses={200: {"description": "업데이트 된 겂이 있을 경우 True"}})
def put_cred_info(
    request: CredRequestBase,
    user_pk: int = Path(gt=0, title="사용자 id"),
    cred_pk: int = Path(gt=0, title="인증 id"),
):
    """인증 정보 수정 (admin을 제외한 사용자는 자신의 인증 정보만 수정 가능)"""
    return put_cred_info_service(user_pk, cred_pk, request)


@router.delete("/{user_pk}/{cred_pk}", response_model=bool, responses={200: {"description": "삭제 된 겂이 있을 경우 True"}})
def delete_cred_info(
    user_pk: int = Path(gt=0, title="사용자 id"),
    cred_pk: int = Path(gt=0, title="인증 id"),
):
    """인증 정보 삭제 (admin을 제외한 사용자는 자신의 인증 정보만 삭제 가능)"""
    return delete_cred_info_service(user_pk, cred_pk)

