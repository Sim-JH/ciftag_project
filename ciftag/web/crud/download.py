import json
from typing import List, Dict, Any

from sqlalchemy import union, between
from kafka import KafkaProducer

from ciftag.settings import env_key
from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.web.crud.common import insert_work_status
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


def send_massage_to_topic(topic: str, messages: List[Dict[str, str]], headers=None):
    # Kafka 메세지 전송
    kafka_producer = KafkaProducer(
        bootstrap_servers=env_key.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    # 낱개 단위 전송, 배치단위 처리
    for message in messages:
        kafka_producer.send(
            topic=topic,
            value=message,
            headers=headers
        )

    kafka_producer.flush()

# def download_image_from_url_service(target_code: str, request):
#     """사이트별 이미지 일괄 다운로드"""
#     request = request.dict()
#     data_pk_list = request.get('data_pk_list')
#
#     if target_code == "1":
#         info_model = PinterestCrawlInfo
#         data_model = PinterestCrawlData
#         join_key = PinterestCrawlData.pint_pk
#         target = "Pinterest"
#     elif target_code == "2":
#         info_model = TumblrCrawlInfo
#         data_model = TumblrCrawlData
#         join_key = TumblrCrawlData.tumb_pk
#         target = "Tumblr"
#     elif target_code == "3":
#         info_model = FlickrCrawlInfo
#         data_model = FlickrCrawlData
#         join_key = FlickrCrawlData.flk_pk
#         target = "Flickr"
#     else:
#         raise CiftagAPIException('Target Not Exist', 404)
#
#     dbm = DBManager()
#
#     # tag + url 가져오기
#     with (dbm.create_session() as session):
#         query = session.query(
#             info_model.id.label("info_id"),
#             info_model.tags,
#             data_model.id.label("data_id"),
#             data_model.title,
#             data_model.image_url,
#         ).join(
#             data_model, info_model.id == join_key
#         )
#
#         if len(data_pk_list):
#             query = query.filter(
#                 data_model.id.in_(data_pk_list)
#             )
#
#         # records = query.order_by(data_model.id).limit(100).all()
#         records = query.order_by(data_model.id).all()
#
#     # orm -> dict
#     records = [dict(record._mapping) for record in records]
#
#     # kafka send
#     send_massage_to_topic(topic=env_key.KAFKA_TARGET_IMAGE_DOWNLOAD_TOPIC, messages=records)
#
#     return len(records)
#

def download_image_by_tags_service(
        tags: List[str], zip_path: str, target_size, threshold: float, model_type: str
):
    def apply_size_filter(_query, _data_model, _target_size):
        # 타겟 이미지 사이즈 범위 조정
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

    work_id = insert_work_status({'work_sta': enums.WorkStatusCode.trigger, 'work_type': enums.WorkTypeCode.download})

    # kafka send
    headers = [
        ('work_id', work_id),
        ('zip_path', zip_path),
        ('threshold', threshold),
        ('model_type', model_type)
    ]
    send_massage_to_topic(
        topic=env_key.KAFKA_TAG_IMAGE_DOWNLOAD_TOPIC, messages=records, headers=headers
    )

    return len(records)



