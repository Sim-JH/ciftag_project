from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session


from ciftag.web.schemas.cred import (
    CredRequestBase,
    CredResponseBase
)

router = APIRouter()


@router.get("/{user_pk}", response_model=List[CredResponseBase])
async def get_cred_list(
    user_pk: int = Path(title="사용자 id", description="0입력 시 전체 조회"),
):
    """인증 정보 가져오기"""
    pass


@router.post("/", response_model=int)
def post_cred_info(
    request: CredRequestBase,
):
    """인증 정보 생성"""
    pass


@router.put("/{user_pk}/{cred_pk}", response_model=int)
def put_cred_info(
    user_pk: int = Path(gt=1, title="사용자 id"),
    cred_pk: int = Path(gt=1, title="인증 id"),
):
    """인증 정보 삭제 (admin을 제외한 사용자는 자신의 인증 정보만 수정 가능)"""
    pass


@router.delete("/{user_pk}/{cred_pk}", response_model=int)
def delete_cred_info(
    user_pk: int = Path(gt=1, title="사용자 id"),
    cred_pk: int = Path(gt=1, title="인증 id"),
):
    """인증 정보 삭제 (admin을 제외한 사용자는 자신의 인증 정보만 삭제 가능)"""
    pass

