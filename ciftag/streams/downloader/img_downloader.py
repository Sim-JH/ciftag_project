import os
import json
import requests
import base64

from datetime import datetime

from ciftag.settings import TIMEZONE, env_key
from ciftag.configuration import conf
from ciftag.integrations.request_session import make_requests
from ciftag.streams.downloader.downloader_interface import ImgDownloaderBase


class ImgDownloadConsumer(ImgDownloaderBase):
    """request 기반 이미지 다운로더 (HPA)"""
    def __init__(self):
        super().__init__(
            topic=env_key.KAFKA_IMAGE_DOWNLOADER_TOPIC,
            group_id="tag_img_download_group",
            log_dir="Download/TAG",
            auto_offset_reset="earliest",
        )

    def _chunk_pins(self, source, chunk_size):
        for i in range(0, len(source), chunk_size):
            yield source[i:i + chunk_size]

    def _retry_or_fail(self, message, retry=False, agt_key=None):
        """실패 시 재시도 혹은 DLQ 전송"""
        # TODO 최대 재시도 제한
        re_message = json.dumps(message).encode('utf-8')
        if retry and message["retry"] < env_key.MAX_TASK_RETRY:
            self.producer.send(env_key.KAFKA_IMAGE_DOWNLOADER_TOPIC, value=re_message).get(timeout=10)
        else:
            self.redis.incrby_key(agt_key, "get_failed")
            pass

    def process_message(self, records):
        """메세지 처리"""
        image_sources = []

        self.logs.log_data(f"Processing tag download messages: {len(records)}")
        self.logs.log_data(f"records: {records}")

        for record in records:
            self.logs.log_data(f"Processing record: {record}")
            headers = {
                key: value.decode('utf-8') if value is not None else None
                for key, value in record.headers
            }
            
            work_id = headers.get('work_id')
            tags = eval(headers.get('tags'))[0]
            zip_path = headers.get('zip_path')
            threshold = headers.get('threshold')
            model_type = headers.get('model_type')
            total_cnt = headers.get('total_cnt')
            api_proxies = headers.get('api_proxies', None)
            ext = headers.get('ext', 'png')

            agt_key = f"work_id:{work_id}"
            # 시작 시간 설정 및 목표 수량(해당 키에 값이 없을 경우)
            self.redis.set_nx(agt_key, 'created_at', datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S'))
            self.redis.set_nx(agt_key, 'total_cnt', total_cnt)

            message = json.loads(record.value.decode("utf-8"))
            self.logs.log_data(f"message: {message}")
            message['retry'] = int(message.get('retry', 0)) + 1

            # 이미지를 저장할 디렉토리
            base_dir = os.path.join(f"{conf.get('dir', 'img_dir')}/Tags", f"{tags.replace('/', '_')}/{model_type}_{threshold}")
            os.makedirs(base_dir, exist_ok=True)

            # 이미지 URL에서 파일 확장자 추출할 경우
            tag = tags.replace('/', '_')
            crawl_idx = message.get('crawl_id')
            target_code = message.get('target_code')
            info_idx = message.get('info_id')
            data_idx = message.get('data_id')
            image_url = message.get('pint_crawl_data_image_url')

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
                    image_sources.append({
                        'work_id': work_id,
                        'base_dir': base_dir,
                        'filename': filename,
                        'zip_path': zip_path,
                        'threshold': threshold,
                        'model_type': model_type,
                        'tags': tags,
                        'source': base64.b64encode(response.content).decode('utf-8')  # 테스트 결과 바이트 이미지를 메세지에 담기에는 무리가 있을듯 TODO: 경로로 변경
                    })
                    # 해당 work_id에 대한 download cnt 증가
                    self.redis.incrby_key(agt_key, "get_complete")
                elif status_code == 404:
                    self.logs.log_data(f'Not Found Error: {image_url}')
                    self.redis.incrby_key(agt_key, "get_failed")
                    continue

            except Exception as e:
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response.status_code in [403, 429]:
                        self._retry_or_fail(message, True)
                    else:
                        self._retry_or_fail(message, True)
                else:
                    if isinstance(e, requests.exceptions.ReadTimeout):
                        self._retry_or_fail(message, True)
                    elif isinstance(e, requests.exceptions.ProxyError):
                        self._retry_or_fail(message, True)
                    else:
                        self.logs.log_data(f'Unexpect Request Error: {e}')
                        self._retry_or_fail(message, False, agt_key=agt_key)

        if len(image_sources):
            self.logs.log_data("End process start send message to sample image filter")
            chunks = self._chunk_pins(image_sources, 3)  # 임시 청크

            for chunk in chunks:
                self.producer.send(env_key.KAFKA_SAMPLE_IMAGE_FILTER_TOPIC, chunk).get(timeout=10)

            # self.producer.send(env_key.KAFKA_SAMPLE_IMAGE_FILTER_TOPIC, image_sources).get(timeout=10)
            self.logs.log_data(f"Batch commit: {len(image_sources)} messages processed.")