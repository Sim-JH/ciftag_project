import os
from datetime import datetime
import requests

import ciftag.utils.logger as logger

from ciftag.configuration import conf
from ciftag.integrations.request_session import make_requests
from ciftag.celery_app import app
from ciftag.ml.filter import ImageFilter
from ciftag.web.crud.core import update_orm, increment_orm
from ciftag.models import (
    PinterestCrawlInfo,
    PinterestCrawlData,
    TumblrCrawlInfo,
    TumblrCrawlData,
    FlickrCrawlInfo,
    FlickrCrawlData
)

logs = logger.Logger(log_dir='Download')


# TODO DB 로깅 추가
@app.task(bind=True, name="ciftag.task.download_images_by_target", max_retries=3)
def download_images_by_target(self, target, records, success_list=None, api_proxies=None, ext='png'):
    """requests 기반 타겟별 이미지 다운로드. 재시도 최대 3회"""
    # TODO 필터링 프리셋
    logs.log_data(f'--- Target: {target} {self.request.retries}회 다운로드 시작. 총 목표 갯수: {len(records)}')

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

    for record in records:
        # 이미지 URL에서 파일 확장자 추출할 경우
        info_idx, tags, data_idx, title, image_url = record.values()
        tag = "_".join(tags)  # TODO tag 여러 개일때의 디렉토리 구조 구조

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

            if response.status_code == 200:
                with open(img_path, 'wb') as f:
                    f.write(response.content)

                success_list.append(data_idx)
                update_orm(
                    data_model, 'id', data_idx, {
                        'download': True, 'img_path': img_path, 'size': os.path.getsize(img_path)
                    }
                )
                increment_orm(info_model, 'id', info_idx, 'downloads')
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
    
    logs.log_data(f'--- Target: {target} {self.request.retries}회 {len(success_list)}개 다운로드')
    
    if len(retry_list) > 0:
        try:
            self.retry(
                exc=Exception(f"Retrying due to retry list for {self.request.retries} times"), countdown=60,
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
    else:
        # 추후 callback 사용 시
        logs.log_data(f'--- Target: {target} 다운로드 종료')
        return {
            'success_list': success_list
        }


# @app.task(bind=True, name="ciftag.task.download_images_by_tags", max_retries=3)
# def download_images_by_tags(
#         self, mode, tags, zip_path, records, threshold, success_list=None, api_proxies=None, ext='png'
# ):
# def download_images_by_tags(
#         mode, tags, zip_path, records, threshold, success_list=None, api_proxies=None, ext='png'
# ):
#     """requests 기반 태그별 이미지 다운로드. 필터 적용 가능. 재시도 최대 3회"""
#     # logs.log_data(f'--- Tags: {tags} {self.request.retries}회 다운로드 시작')
#
#     # 이미지를 저장할 디렉토리
#     base_dir = os.path.join(f'{conf.get('dir', 'img_dir')}/Tags', '_'.join(tags))
#     os.makedirs(base_dir, exist_ok=True)
#
#     if success_list is None:
#         success_list = []
#
#     retry_list = []
#     fail_list = []
#
#     # 이미지 필터 모듈 초기화
#     image_filter = ImageFilter(
#         sample_image_path=zip_path,
#         target_tags=tags,
#         threshold=threshold,
#         mode='byte'
#     )
#
#     image_sources = []
#
#     for idx, record in enumerate(records):
#         # 이미지 URL에서 파일 확장자 추출할 경우
#         tag = '_'.join(tags)
#         crawl_idx, info_idx, data_idx, image_url = record.values()
#
#         # 이미지 파일명 생성
#         filename = f"{tag}_{crawl_idx}_{info_idx}_{data_idx}"
#
#         # 이미지 Get
#         try:
#             # 세션 연결 실패시 총 3회 재시도
#             response = make_requests(
#                 url=image_url,
#                 api_proxies=api_proxies,
#                 method='GET',
#                 params=None,
#                 headers=None
#             )
#
#             if response.status_code == 200:
#                 image_sources.append((filename, response.content))
#
#         except Exception as e:
#             if isinstance(e, requests.exceptions.HTTPError):
#                 if e.response.status_code in [403, 429]:
#                     retry_list.append(record)
#                 else:
#                     retry_list.append(record)
#             else:
#                 if isinstance(e, requests.exceptions.ReadTimeout):
#                     retry_list.append(record)
#                 elif isinstance(e, requests.exceptions.ProxyError):
#                     retry_list.append(record)
#                 else:
#                     logs.log_data(f'Unexpect Request Error: {e}')
#                     retry_list.append(record)
#
#     filtered_image_source = image_filter.combined_filtering(mode, image_sources)
#
#     for file_name, image_source in filtered_image_source:
#         with open(os.path.join(base_dir, file_name), 'wb') as f:
#             f.write(image_source)

    # logs.log_data(f'--- Tags: {tags} {self.request.retries}회 {len(success_list)}개 다운로드')

    # if len(retry_list) > 0:
    #     try:
    #         self.retry(
    #             exc=Exception(f"Retrying due to retry list for {self.request.retries} times"), countdown=60,
    #             kwargs={
    #                 'mode': mode,
    #                 'tags': "/".join(tags),
    #                 'zip_path': zip_path,
    #                 'records': records,
    #                 'threshold': threshold,
    #                 'success_list': success_list,
    #                 'api_proxies': api_proxies,
    #                 'ext': ext
    #             }
    #         )  # 차단 시 재시도
    #     except self.MaxRetriesExceededError:
    #         logs.log_data(f"Max retries exceeded for record {fail_list}", "error")
    # else:
    #     # 추후 callback 사용 시
    #     logs.log_data(f'--- Tags: {tags} 다운로드 종료')
    #     return {
    #         'success_list': success_list
    #     }
