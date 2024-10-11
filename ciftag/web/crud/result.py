from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.models import (
    CrawlRequestInfo,
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData
)
from ciftag.web.crud.core import (
    select_orm,
    search_orm,
    insert_orm,
    update_orm,
    delete_orm
)

from sqlalchemy import union_all, text


async def get_cred_info_service(target_code: str, user_pk: int):
    dbm = DBManager()

    with dbm.create_session() as session:
        def base_info_query(info_model):
            info_columns = list(info_model.__table__.columns)

            sub_query = session.query(
                *info_columns,
                CrawlRequestInfo.user_pk,
                CrawlRequestInfo.run_on,
                CrawlRequestInfo.target_code
            ).join(
                CrawlRequestInfo, CrawlRequestInfo.id == info_model.crawl_pk
            )

            if user_pk:
                sub_query = sub_query.filter(
                    CrawlRequestInfo.user_pk == user_pk
                )

            return sub_query

        if target_code == "0":
            queries = [base_info_query(model) for model in (PinterestCrawlInfo, TumblrCrawlInfo, FlickrCrawlInfo)]
            query = queries.pop().union_all(*queries)
        elif target_code == "1":
            query = base_info_query(PinterestCrawlInfo)
        elif target_code == "2":
            query = base_info_query(TumblrCrawlInfo)
        elif target_code == "3":
            query = base_info_query(FlickrCrawlInfo)
        else:
            raise CiftagAPIException('Target Not Exist', 404)

        records = query.all()

    return records
