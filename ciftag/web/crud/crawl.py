from datetime import datetime
from typing import List, Optional


from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.models import CredentialInfo, CrawlRequestInfo, enums
from ciftag.web.crud.core import (
    insert_orm,
    update_orm
)
from ciftag.orchestrator.crawl import CrawlTriggerDispatcher


async def get_crawl_req_service(
    crawl_pk: int,
    user_pk: Optional[int],
    target_code: Optional[str],
    run_on: Optional[int],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    tags: List[str]
):
    dbm = DBManager()

    with dbm.create_session() as session:
        query = session.query(
            CrawlRequestInfo
        )

        if crawl_pk:
            query = query.filter(CrawlRequestInfo.id == crawl_pk)

        if user_pk:
            query = query.filter(CrawlRequestInfo.user_pk == user_pk)

        if target_code:
            query = query.filter(CrawlRequestInfo.target_code == target_code)

        if run_on:
            query = query.filter(CrawlRequestInfo.run_on == run_on)

        if start_time:
            query = query.filter(CrawlRequestInfo.created_at >= start_time)

        if end_time:
            query = query.filter(CrawlRequestInfo.created_at <= end_time)

        if len(tags) > 0:
            query = query.filter(
                CrawlRequestInfo.tags.op('~')('|'.join(tags))  # 정규식 기반 검색
            )

        records = query.order_by(CrawlRequestInfo.id).all()

    return records


async def add_crawl_info_with_trigger(data):
    # 태그 처리
    tag_list = data['tags']

    # 단일 태그만 허용하는 사이트
    if (data['target_code'] == "pinterest" or data['target_code'] == "tumblr") and len(tag_list) > 0:
        raise CiftagAPIException('Target is Accept Only One Tag', 422)

    data['tags'] = "/".join(tag_list)

    # 작업 정보 등록
    crawl_pk = insert_orm(
        CrawlRequestInfo,
        {
            'user_pk': data['user_pk'],
            'run_on': data['run_on'],
            'target_code': data['target_code'],
            'triggered': False,
            'tags': data['tags'],
            'cnt': data['cnt'],
            'etc': data.get('etc')
        },
        True
    )

    dbm = DBManager()

    # 사용자에게 목표 사이트에 사용 가능한 id 있는지 확인
    with dbm.create_session() as session:
        records = session.query(
            CredentialInfo.id,
            CredentialInfo.cred_ident,
            CredentialInfo.cred_pw,
            CredentialInfo.status_code
        ).filter(
            CredentialInfo.user_pk == data['user_pk'],
            CredentialInfo.target_code == data['target_code'],
        ).order_by(CredentialInfo.updated_at).all()

    active_list = []

    for cred_pk, cred_id, cred_pw, status_code in records:
        if status_code == enums.StatusCode.active:
            active_list.append(
                (cred_pk, cred_id, cred_pw)
            )

    if len(active_list) == 0:
        update_orm(
            CrawlRequestInfo, 'id', crawl_pk, {'triggered': False, 'etc': 'Not Found Active Account'}
        )
        raise CiftagAPIException('Not Found Active Account', 403)

    # 작업 실행
    dispatcher = CrawlTriggerDispatcher(data)
    # aws sqs 이용 시 비번 crypto
    dispatcher.set_cred_info(active_list, crypto=True if data['run_on'] == enums.RunOnCode.aws else False)
    work_id = dispatcher.run(crawl_pk)
    update_orm(CrawlRequestInfo, 'id', crawl_pk, {'triggered': True})

    return work_id
