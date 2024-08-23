from typing import List, Union


from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.models import CredentialInfo, CrawlRequestInfo
from ciftag.web.crud.core import (
    insert_orm,
    update_orm
)
from ciftag.orchestrator.crawl import CrawlTriggerDispatcher


def get_crawl_info_with_service(
    crawl_pk: int,
    user_pk: Union[int, None],
    target_code: Union[str, None],
    result_code: Union[str, None],
    run_on: Union[int, None],
    tags: List[str],
):
    pass


def add_crawl_info_with_trigger(request):
    # 작업 정보 등록
    crawl_pk = insert_orm(CrawlRequestInfo, request)

    data = request.dict()
    dbm = DBManager()

    # 사용자에게 목표 사이트에 사용 가능한 id 있는지 확인
    with dbm.create_session() as session:
        records = session.query(
            CredentialInfo.id,
            CredentialInfo.user_id,
            CredentialInfo.user_pw,
            CredentialInfo.status_code
        ).filter(
            CredentialInfo.user_pk == data['user_pk']
        ).order_by(CredentialInfo.updated_at).all()

    active_list = []

    for cred_pk, cred_id, cred_pw, status_code in records:
        if status_code == "0":
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
    dispatcher.set_cred_info(active_list)
    work_id = dispatcher.run(crawl_pk)

    return work_id
