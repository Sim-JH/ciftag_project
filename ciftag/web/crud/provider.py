import os
import cv2
from ciftag.configuration import conf
from ciftag.ml.detect_face import FaceCropper

from sqlalchemy import union, between

from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.database import DBManager
from ciftag.utils.apis import provide_to_zipfile
from ciftag.models import (
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData,
)


def provide_face_crop_image_service(target_code: str, start_idx: int, end_idx: int, resize: int):
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

    with dbm.create_session() as session:
        records = session.query(
            info_model.id.label("info_id"),
            info_model.tags,
            data_model.id.label("data_id"),
            data_model.title,
            data_model.img_path,
        ).join(
            data_model, info_model.id == join_key
        ).filter(
            between(
                data_model.id,
                start_idx,
                end_idx
            )
        ).filter(
            data_model.download == True
        ).order_by(data_model.id).all()

    # orm -> dict
    records = [dict(record._mapping) for record in records]

    face_cropper = FaceCropper()
    crop_file_list = []
    
    for record in records:
        img_path = record['img_path']
        output_image = face_cropper.detect_and_crop(img_path)

        if output_image is None or output_image.size == 0:
            continue

        if resize:
            output_image = face_cropper.resize_image(output_image, resize)

        # 이미지를 저장할 디렉토리
        base_dir = os.path.join(f'{conf.get('dir', 'img_dir')}/Crop', target)
        os.makedirs(base_dir, exist_ok=True)

        # 이미지 파일명 생성
        tag = record['tags'].replace('/', '_')
        info_id = record['info_id']
        data_id = record['data_id']
        title = record['title']

        # 타이틀은 10자까지만
        title = title[:10].rstrip() if len(title) > 10 else title
        ext = "png"
        filename = f"{target}_{tag}_{info_id}_{data_id}_{title}.{ext}"
        save_path = f"{base_dir}/{filename}"

        # 결과 저장
        cv2.imwrite(save_path, output_image)
        crop_file_list.append(save_path)

    zip_path = f"{target}_{start_idx}_{end_idx}_{len(crop_file_list)}.zip"

    provide_to_zipfile(zip_path, crop_file_list)

    return zip_path
