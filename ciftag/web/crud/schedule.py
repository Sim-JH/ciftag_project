from typing import List

from ciftag.exceptions import CiftagAPIException
from ciftag.models import PinterestCrawlInfo, PinterestCrawlData
from ciftag.integrations.database import DBManager
from ciftag.celery_app import app


def download_image_urls(target_code: str, data_pk_list: List[int]):
    if target_code == "1":
        info_model = PinterestCrawlInfo
        data_model = PinterestCrawlData
        join_key = PinterestCrawlData.pint_pk
        target = "Pinterest"
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
        "ciftag.task.download_images",
        kwargs={
            'target': target,
            'records': records,
        }
    )

    download_img_s.apply_async()

    return len(records)
