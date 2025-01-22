# TODO: download celery task -> kafka
# TODO: 메세지는 낱개로 전해질 거고 이걸 배치로 빨아들어서 처리할거임
# TODO: 상위에서 이미지 소스(바이트)를 다운로드 하고 이걸 하위 DAG로 전달?
# TODO: 작업 흐름 관리는 어떻게 할지. 크롤링처럼 레디스 환경 분리 감안? 아니면 일괄?


import os
import json
import requests
import base64

from ciftag.settings import TIMEZONE, env_key
from ciftag.ml.filter import ImageFilter
from ciftag.web.crud.common import upsert_img_match
from ciftag.streams.downloader.img_downloader import ImgDownloaderBase


class SampleImgFilter(ImgDownloaderBase):
    """샘플 이미지 기반 다운로드 이미지 필터링 및 파일변환(분리 고려)"""
    def __init__(self):
        super().__init__(
            topic=env_key.KAFKA_SAMPLE_IMAGE_FILTER_TOPIC,
            group_id="sample_img_filter_group",
            log_dir="Download/TAG",
            auto_offset_reset="earliest",
        )

    def _handle_failed(self, message):
        """실패 처리"""
        pass

    def _get_task_status(self, agt_key):
        task_status = self.redis.get_all(agt_key)
        return {
            "total_cnt": int(task_status.get("total_cnt", 0)),
            "get_complete": int(task_status.get("get_complete", 0)),
            "get_failed": int(task_status.get("get_failed", 0)),
            "created_at": str(task_status.get("created_at"))
        }

    @staticmethod
    def _add_to_dict(store, key, value):
        if key not in store:
            store[key] = []
        store[key].append(value)

    def _convert_to_img(self, filtered_image_source, agt_key, base_dir, model_type, threshold):
        # 이미지 쓰기 + 매칭 테이블 갱신 
        self.logs.log_data(f"이미지 쓰기 시작: {len(filtered_image_source)}")
        for file_name, image_source in filtered_image_source:
            with open(os.path.join(f'{base_dir}', file_name), 'wb') as f:
                self.redis.incrby_key(agt_key, "image_cnt")
                f.write(image_source)

            _name = file_name.rsplit('.', 1)[0].split('_')
            
            # 이미지 매치 테이블 갱신
            upsert_img_match(
                data_id=int(_name[-1]),
                target_code=_name[1],
                filter_dict={model_type: float(threshold)}
            )

    def _run_image_filter(self, image_sources, zip_path, threshold, model_type, tags):
        # 이미지 필터 모듈 초기화
        image_filter = ImageFilter(
            sample_image_path=zip_path,
            threshold=threshold,
            model_type=model_type
        )
        self.logs.log_data(f'--- Tags: {model_type} {tags} 이미지 필터링 실행')
        return image_filter.combined_filtering('byte', image_sources)

    def process_message(self, records):
        """메세지 처리"""
        image_source_store = {}  # pod별 프로세스 메모리에 pull한 byte 이미지 보관 (메모리 해제 관리)

        self.logs.log_data(f"Processing tag download messages: {len(records)}")

        for record in records:
            messages = json.loads(record.value.decode("utf-8"))
            for message in messages:
                work_id = message.get('work_id')
                base_dir = message.get('base_dir')
                filename = message.get('filename')
                zip_path = message.get('zip_path')
                threshold = float(message.get('threshold'))
                model_type = message.get('model_type')
                tags = message.get('tags')
                source = base64.b64decode(message.get('source'))
                agt_key = f"work_id:{work_id}"

                task_status = self._get_task_status(agt_key)
                total_cnt = task_status.get('total_cnt')
                get_complete = task_status.get('get_complete')
                get_failed = task_status.get('get_failed')

                self._add_to_dict(image_source_store, agt_key, (filename, source))
                
                # 다운로드 완료된 데이터들에 대한 필터링 수행
                if total_cnt == (get_complete + get_failed):
                    # TODO: 집계후 바로 작업 -> 필터링 작업 이전에 집계용 토픽에서 다운로드 완료한 작업만 내려오도록 변경
                    image_sources = image_source_store.get(agt_key)
                    # 필터링
                    filtered_image_source = self._run_image_filter(image_sources, zip_path, threshold, model_type, tags)
                    self.logs.log_data(f"필터링 완료 이미지 수: {len(filtered_image_source)}")
                    # 파일 저장
                    self._convert_to_img(filtered_image_source, agt_key, base_dir, model_type, threshold)
