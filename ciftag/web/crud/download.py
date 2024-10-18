import zipfile
from typing import List, Optional

from sqlalchemy import union, between

from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.celery_app import app
from ciftag.models import (
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData,
    CrawlRequestInfo,
    enums
)


def download_image_from_url_service(target_code: str, request):
    request = request.dict()
    data_pk_list = request.get('data_pk_list')

    if target_code == "1":
        info_model = PinterestCrawlInfo
        data_model = PinterestCrawlData
        join_key = PinterestCrawlData.pint_pk
        target = "Pinterest"
    elif target_code == "2":
        info_model = TumblrCrawlInfo
        data_model = TumblrCrawlData
        join_key = TumblrCrawlData.tumb_pk
        target = "Tumblr"
    elif target_code == "3":
        info_model = FlickrCrawlInfo
        data_model = FlickrCrawlData
        join_key = FlickrCrawlData.flk_pk
        target = "Flickr"
    else:
        raise CiftagAPIException('Target Not Exist', 404)

    dbm = DBManager()

    # tag + url 가져오기
    with dbm.create_session() as session:
        records = session.query(
            info_model.id.label("info_id"),
            info_model.tags,
            data_model.id.label("data_id"),
            data_model.title,
            data_model.image_url,
        ).join(
            data_model, info_model.id == join_key
        ).filter(
            data_model.id.in_(data_pk_list)
        ).order_by(data_model.id).all()

    # orm -> dict
    records = [dict(record._mapping) for record in records]

    # celery run
    download_img_s = app.signature(
        "ciftag.task.download_images_by_target",
        kwargs={
            'target': target,
            'records': records,
        }
    )

    download_img_s.apply_async()

    return len(records)


def download_image_by_tags_service(
        tags: List[str], zip_path: str, target_size, threshold: float, model_type: str
):
    def apply_size_filter(_query, _data_model, _target_size):
        return _query.filter(
            between(
                _data_model.width,
                _target_size[0] * 0.9,
                _target_size[0] * 1.1
            ),
            between(
                _data_model.height,
                _target_size[1] * 0.9,
                _target_size[1] * 1.1
            )
        )

    dbm = DBManager()

    # tag + url 가져오기
    with dbm.create_session() as session:
        pint = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            CrawlRequestInfo.target_code.label('target_code'),
            PinterestCrawlInfo.id.label('info_id'),
            PinterestCrawlData.id.label('data_id'),
            PinterestCrawlData.image_url,
        ).join(
            PinterestCrawlInfo, PinterestCrawlData.pint_pk == PinterestCrawlInfo.id
        ).join(
            CrawlRequestInfo, PinterestCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            PinterestCrawlInfo.tags.in_(tags),
            # PinterestCrawlData.download == False
        )

        thumb = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            CrawlRequestInfo.target_code.label('target_code'),
            TumblrCrawlInfo.id.label('info_id'),
            TumblrCrawlData.id.label('data_id'),
            TumblrCrawlData.image_url,
        ).join(
            TumblrCrawlInfo, TumblrCrawlData.tumb_pk == TumblrCrawlInfo.id
        ).join(
            CrawlRequestInfo, TumblrCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            TumblrCrawlInfo.tags.in_(tags),
            # TumblrCrawlData.download == False
        )

        flk = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            CrawlRequestInfo.target_code.label('target_code'),
            FlickrCrawlInfo.id.label('info_id'),
            FlickrCrawlData.id.label('data_id'),
            FlickrCrawlData.image_url,
        ).join(
            FlickrCrawlInfo, FlickrCrawlData.flk_pk == FlickrCrawlInfo.id
        ).join(
            CrawlRequestInfo, FlickrCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            FlickrCrawlInfo.tags.op('~')('|'.join(tags)),  # 정규식 기반 검색
            # FlickrCrawlData.download == False
        )

        # Full-Text Search (Postgresql only) 형태소 기반 검색시
        # or_(
        #     func.to_tsvector('korean', FlickrCrawlInfo.tags).match(tags),
        #     func.to_tsvector('english', FlickrCrawlInfo.tags).match(tags)
        # )

        if target_size:
            pint = apply_size_filter(pint, PinterestCrawlData, target_size)
            thumb = apply_size_filter(thumb, TumblrCrawlData, target_size)
            flk = apply_size_filter(flk, FlickrCrawlData, target_size)

        # query = union(pint, thumb, flk).limit(100)
        query = union(pint, thumb, flk)
        records = session.execute(query).fetchall()

    # orm -> dict
    serialized_records = []

    for record in records:
        record_dict = dict(record._mapping)
        # enums 필드 처리
        if isinstance(record_dict.get('target_code'), enums.CrawlTargetCode):
            record_dict['target_code'] = record_dict['target_code'].name

        serialized_records.append(record_dict)

    # celery run
    download_img_tag_s = app.signature(
        "ciftag.task.download_images_by_tags",
        kwargs={
            'tags': "/".join(tags),
            'zip_path': zip_path,
            'records': serialized_records,
            'threshold': threshold,
            'model_type': model_type,
        }
    )

    download_img_tag_s.apply_async()

    return len(records)



