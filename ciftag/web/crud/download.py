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
    CrawlRequestInfo
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
        tags: List[str], zip_path: str, target_size, threshold: float
):
    dbm = DBManager()

    # tag + url 가져오기
    with (dbm.create_session() as session):
        pint = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            PinterestCrawlInfo.id.label('info_id'),
            PinterestCrawlData.id.label('data_id'),
            PinterestCrawlData.image_url,
        ).join(
            PinterestCrawlInfo, PinterestCrawlData.pint_pk == PinterestCrawlInfo.id
        ).join(
            CrawlRequestInfo, PinterestCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            PinterestCrawlInfo.tags.in_(tags),
        )

        thumb = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            TumblrCrawlInfo.id.label('info_id'),
            TumblrCrawlData.id.label('data_id'),
            TumblrCrawlData.image_url,
        ).join(
            TumblrCrawlInfo, TumblrCrawlData.tumb_pk == TumblrCrawlInfo.id
        ).join(
            CrawlRequestInfo, TumblrCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            TumblrCrawlInfo.tags.in_(tags)
        )

        flk = session.query(
            CrawlRequestInfo.id.label('crawl_id'),
            FlickrCrawlInfo.id.label('info_id'),
            FlickrCrawlData.id.label('data_id'),
            FlickrCrawlData.image_url,
        ).join(
            FlickrCrawlInfo, FlickrCrawlData.flk_pk == FlickrCrawlInfo.id
        ).join(
            CrawlRequestInfo, FlickrCrawlInfo.crawl_pk == CrawlRequestInfo.id
        ).filter(
            FlickrCrawlInfo.tags.op('~')('|'.join(tags))  # 정규식 기반 검색
        )

        # Full-Text Search (Postgresql only) 형태소 기반 검색시
        # or_(
        #     func.to_tsvector('korean', FlickrCrawlInfo.tags).match(tags),
        #     func.to_tsvector('english', FlickrCrawlInfo.tags).match(tags)
        # )

        if target_size:
            pint.filter(
                between(
                    PinterestCrawlData.width,
                    target_size[0] * 0.9,
                    target_size[0] * 1.1
                ),
                # height가 target_size[1]의 ±10% 내외인지 확인
                between(
                    PinterestCrawlData.height,
                    target_size[1] * 0.9,
                    target_size[1] * 1.1
                ),
            )

            thumb.filter(
                between(
                    TumblrCrawlData.width,
                    target_size[0] * 0.9,
                    target_size[0] * 1.1
                ),
                # height가 target_size[1]의 ±10% 내외인지 확인
                between(
                    TumblrCrawlData.height,
                    target_size[1] * 0.9,
                    target_size[1] * 1.1
                ),
            )

            flk.filter(
                between(
                    FlickrCrawlData.width,
                    target_size[0] * 0.9,
                    target_size[0] * 1.1
                ),
                # height가 target_size[1]의 ±10% 내외인지 확인
                between(
                    FlickrCrawlData.height,
                    target_size[1] * 0.9,
                    target_size[1] * 1.1
                ),
            )

        query = union(pint, thumb, flk)
        records = session.execute(query).fetchall()

    # orm -> dict
    records = [dict(record._mapping) for record in records]

    # celery run
    download_img_tag_s = app.signature(
        "ciftag.task.download_images_by_tags",
        kwargs={
            'tags': "/".join(tags),
            'zip_path': zip_path,
            'records': records,
            'threshold': threshold,
        }
    )

    download_img_tag_s.apply_async()

    return len(records)



