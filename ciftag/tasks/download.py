import os
from tqdm import tqdm
from datetime import datetime
import requests

import ciftag.utils.logger as logger

from ciftag.configuration import conf
from ciftag.integrations.request_session import make_requests
from ciftag.integrations.elastic import ESManager
from ciftag.celery_app import app
from ciftag.ml.filter import ImageFilter
from ciftag.ml.gen_dec import ImageDescriber
from ciftag.web.crud.core import insert_orm, update_orm, increment_orm
from ciftag.web.crud.common import upsert_img_match
from ciftag.web.crud.common import insert_work_status, update_work_status
from ciftag.models import (
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData,
    ImageTagMeta,
    enums
)

logs = logger.Logger(log_dir='Download')


@app.task(bind=True, name="ciftag.task.download_images_by_target", max_retries=3)
def download_images_by_target(self, target, records, success_list=None, api_proxies=None, ext='png'):
    """requests 기반 타겟별 이미지 다운로드. 재시도 최대 3회
    다운로드를 먼저 수행한 이후 해당 파일들에 대한 메타 업데이트
    """
    logs.log_data(f'--- Target: {target} {self.request.retries+1}회 다운로드 시작. 총 목표 갯수: {len(records)}')
    work_id = insert_work_status({'work_sta': enums.WorkStatusCode.trigger, 'work_type': enums.WorkTypeCode.download})

    # 이미지를 저장할 디렉토리
    base_dir = os.path.join(f'{conf.get('dir', 'img_dir')}/Target', target)
    os.makedirs(base_dir, exist_ok=True)

    if success_list is None:
        success_list = []

    retry_list = []
    fail_list = []

    if target == "Pinterest":
        info_model = PinterestCrawlInfo
        data_model = PinterestCrawlData
    elif target == "Tumblr":
        info_model = TumblrCrawlInfo
        data_model = TumblrCrawlData
    elif target == "Flickr":
        info_model = FlickrCrawlInfo
        data_model = FlickrCrawlData

    target_code = enums.CrawlTargetCode[target.lower()].name
    logs.log_data(f'--- Tags: {target} 이미지 캐시 다운로드')

    for record in records:
        # 이미지 URL에서 파일 확장자 추출할 경우
        info_idx, tags, data_idx, title, image_url = record.values()
        tag = tags.replace(',', '_')

        # 타이틀은 10자까지만
        title = title[:10].rstrip() if len(title) > 10 else title

        # 이미지 파일명 생성
        filename = f"{tag}_{title}_{info_idx}_{data_idx}.{ext}"
        img_path = f"{base_dir}/{filename}"

        # 이미지 다운로드 및 저장
        try:
            # 세션 연결 실패시 총 3회 재시도
            response = make_requests(
                url=image_url,
                api_proxies=api_proxies,
                method='GET',
                params=None,
                headers=None
            )

            status_code = response.status_code

            if status_code == 200:
                with open(img_path, 'wb') as f:
                    f.write(response.content)

                update_orm(
                    data_model, 'id', data_idx, {
                        'download': True, 'img_path': img_path, 'size': os.path.getsize(img_path)
                    }
                )
                increment_orm(info_model, 'id', info_idx, 'downloads')
                success_list.append((data_idx, img_path, tags))
            else:
                logs.log_data(
                    f'response error: {response.status_code} - {response.reason}: {response.text}',
                    'warning'
                )
                fail_list.append(data_idx)

        except Exception as e:
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code in [403, 429]:
                    retry_list.append(record)
                else:
                    retry_list.append(record)
            else:
                if isinstance(e, requests.exceptions.ReadTimeout):
                    retry_list.append(record)
                elif isinstance(e, requests.exceptions.ProxyError):
                    retry_list.append(record)
                else:
                    logs.log_data(f'Unexpect Request Error: {e}')
                    retry_list.append(record)

    update_work_status(work_id, {'work_sta': enums.WorkStatusCode.download})

    image_describer = ImageDescriber(
        model_type='BLIP',
        translate=True
    )

    logs.log_data(f'--- Tags: {target} 이미지 메타 생성')
    img_decs = image_describer.process_image(
        success_list,
        'path'
    )

    # 이미지 메타 쓰기 & 엘리스틱 서치 색인
    es_m = ESManager()
    for data_idx, description in img_decs:
        body = {
            "data_pk": data_idx,
            "target_code": target_code,
            "description": description
        }

        tag_meta_id = insert_orm(
            ImageTagMeta,
            body,
            True
        )

        es_m.index_to_es(
            'image_tag_meta',
            tag_meta_id,
            body,
        )

    logs.log_data(f'--- Target: {target} {self.request.retries+1}회 {len(success_list)}개 다운로드')
    update_work_status(work_id, {'work_sta': enums.WorkStatusCode.success})
    
    if len(retry_list) > 0:
        try:
            self.retry(
                exc=Exception(f"Retrying due to retry list for {self.request.retries+1} times"), countdown=60,
                kwargs={
                    'target': target,
                    'records': retry_list,
                    'success_list': success_list,
                    'api_proxies': api_proxies,
                    'ext': ext
                }
            )  # 차단 시 재시도
        except self.MaxRetriesExceededError:
            logs.log_data(f"Max retries exceeded for record {fail_list}", "error")
            update_work_status(work_id, {'work_sta': enums.WorkStatusCode.failed})
    else:
        # 추후 callback 사용 시
        logs.log_data(f'--- Target: {target} 다운로드 종료')
        return {
            'success_list': success_list
        }


@app.task(bind=True, name="ciftag.task.download_images_by_tags", max_retries=3)
def download_images_by_tags(
        self, tags, zip_path, records, threshold, model_type, filtered_list=None, api_proxies=None, ext='png'
):
    """requests 기반 태그별 이미지 다운로드. 필터 적용 가능. 재시도 최대 3회
    필터링이 완료된 이미지를 대상으로 다운로드
    """
    logs.log_data(f'--- Tags: {model_type} {tags} {self.request.retries+1}회 다운로드. 시작 총 목표 갯수: {len(records)}')
    work_id = insert_work_status({'work_sta': enums.WorkStatusCode.trigger, 'work_type': enums.WorkTypeCode.download})

    # 이미지를 저장할 디렉토리
    base_dir = os.path.join(f'{conf.get('dir', 'img_dir')}/Tags', f'{tags.replace('/', '_')}/{model_type}_{threshold}')
    os.makedirs(base_dir, exist_ok=True)

    if filtered_list is None:
        filtered_list = []

    retry_list = []
    fail_list = []

    image_sources = []

    logs.log_data(f'--- Tags: {model_type} {tags} 이미지 캐시 다운로드')
    for idx, record in tqdm(enumerate(records)):
        # 이미지 URL에서 파일 확장자 추출할 경우
        tag = tags.replace('/', '_')
        crawl_idx, target_code, info_idx, data_idx, image_url = record.values()

        # 이미지 파일명 생성
        filename = f"{tag}_{target_code}_{crawl_idx}_{info_idx}_{data_idx}.{ext}"

        # 이미지 Get
        try:
            # 세션 연결 실패시 총 3회 재시도
            response = make_requests(
                url=image_url,
                api_proxies=api_proxies,
                method='GET',
                params=None,
                headers=None
            )
            status_code = response.status_code

            if status_code == 200:
                image_sources.append((filename, response.content))
            elif status_code == 404:
                # TODO Not Found 일 때의 DB 처리
                logs.log_data(f'Not Found Error: {image_url}')
                continue

        except Exception as e:
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code in [403, 429]:
                    retry_list.append(record)
                else:
                    retry_list.append(record)
            else:
                if isinstance(e, requests.exceptions.ReadTimeout):
                    retry_list.append(record)
                elif isinstance(e, requests.exceptions.ProxyError):
                    retry_list.append(record)
                else:
                    logs.log_data(f'Unexpect Request Error: {e}')
                    retry_list.append(record)

    # 이미지 필터 모듈 초기화
    image_filter = ImageFilter(
        sample_image_path=zip_path,
        threshold=threshold,
        model_type=model_type
    )

    logs.log_data(f'--- Tags: {model_type} {tags} 이미지 필터링 실행')
    filtered_image_source = image_filter.combined_filtering('byte', image_sources)

    # 이미지 쓰기 + 매칭 테이블 갱신
    for file_name, image_source in filtered_image_source:
        with open(os.path.join(f'{base_dir}', file_name), 'wb') as f:
            filtered_list.append(file_name)
            f.write(image_source)

        _name = file_name.rsplit('.', 1)[0].split('_')

        upsert_img_match(
            data_id=int(_name[-1]),
            target_code=_name[1],
            filter_dict={model_type: float(threshold)}
        )

    logs.log_data(f'--- Tags: {tags} {self.request.retries+1}회 {len(filtered_list)}개 필터링 완료 후 다운로드')
    update_work_status(work_id, {'work_sta': enums.WorkStatusCode.success})

    if len(retry_list) > 0:
        try:
            self.retry(
                exc=Exception(f"Retrying due to retry list for {self.request.retries+1} times"), countdown=60,
                kwargs={
                    'tags': "/".join(tags),
                    'zip_path': zip_path,
                    'records': records,
                    'threshold': threshold,
                    'filtered_list': filtered_list,
                    'api_proxies': api_proxies,
                    'ext': ext
                }
            )  # 차단 시 재시도
        except self.MaxRetriesExceededError:
            logs.log_data(f"Max retries exceeded for record {fail_list}", "error")
            update_work_status(work_id, {'work_sta': enums.WorkStatusCode.failed})
    else:
        # 추후 callback 사용 시
        logs.log_data(f'--- Tags: {model_type} {tags} 다운로드 종료')
        os.remove(zip_path)  # 샘플이미지 삭제
        return {
            'filtered_list': filtered_list
        }
