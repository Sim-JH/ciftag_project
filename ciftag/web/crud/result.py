from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.integrations.elastic import ESManager
from ciftag.web.schemas.result import TagMetaResponse
from ciftag.models import (
    CrawlRequestInfo,
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData,
    enums
)


async def get_target_crawl_info_service(target_code: str, user_pk: int):
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


async def get_target_crawl_data_service(
        target_code: str,
        user_pk: int,
        min_height=None,
        max_height=None,
        min_width=None,
        max_width=None,
):
    dbm = DBManager()

    target_models = {
        "1": (PinterestCrawlInfo, PinterestCrawlData, PinterestCrawlData.pint_pk),
        "2": (TumblrCrawlInfo, TumblrCrawlData, TumblrCrawlData.tumb_pk),
        "3": (FlickrCrawlInfo, FlickrCrawlData, FlickrCrawlData.flk_pk),
    }

    with dbm.create_session() as session:
        def base_info_query(info_model, data_model, join_key):
            data_columns = list(data_model.__table__.columns)

            sub_query = session.query(
                info_model.tags,
                CrawlRequestInfo.user_pk,
                CrawlRequestInfo.run_on,
                CrawlRequestInfo.target_code,
                *data_columns,
            ).join(
                data_model, info_model.id == join_key
            ).join(
                CrawlRequestInfo, CrawlRequestInfo.id == info_model.crawl_pk
            )

            if user_pk:
                sub_query = sub_query.filter(
                    CrawlRequestInfo.user_pk == user_pk
                )

            sub_query.filter(data_model.image_url is not None)

            if min_height is not None:
                sub_query = sub_query.filter(data_model.height >= min_height)
            if max_height is not None:
                sub_query = sub_query.filter(data_model.height <= max_height)

            if min_width is not None:
                sub_query = sub_query.filter(data_model.width >= min_width)
            if max_width is not None:
                sub_query = sub_query.filter(data_model.width <= max_width)

            return sub_query

        if target_code == "0":
            queries = [
                base_info_query(info_model, data_model, join_key)
                for info_model, data_model, join_key in target_models.values()
            ]
            query = queries.pop().union_all(*queries)
        elif target_code in target_models:
            info_model, data_model, join_key = target_models[target_code]
            query = base_info_query(info_model, data_model, join_key)
        else:
            raise CiftagAPIException('Target Not Exist', 404)

        records = query.all()

    return records


async def get_result_img_by_dec_service(description: str):
    es_m = ESManager()
    body = {
        "query": {
            "match": {
                "description": description
            }
        }
    }

    records = es_m.search_es_index(index_name="image_tag_meta", body=body)
    
    return [
        TagMetaResponse(
            id=record['id'],
            data_pk=record['data_pk'],
            target_code=enums.CrawlTargetCode[record['target_code']],
            description=record['description']
        )
        for record in records
    ]
