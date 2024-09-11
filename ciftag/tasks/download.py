import os
import requests

import ciftag.utils.logger as logger

from ciftag.integrations.request_session import make_requests
from ciftag.configuration import conf
from ciftag.celery_app import app

logs = logger.Logger(log_dir='Download')


@app.task(bind=True, name="ciftag.task.download_images")
def download_images(target, records, api_proxies=None, ext='png'):
    logs.log_data(f'--- {target} 다운로드 시작')

    # 이미지를 저장할 디렉토리
    base_dir = os.path.join(conf.get('dir', 'img_dir'), target)
    os.makedirs(base_dir, exist_ok=True)

    for idx, (tags, title, image_url) in enumerate(records, 1):
        # 이미지 URL에서 파일 확장자 추출할 경우
        # parsed_url = urlparse(image_url)
        # ext = os.path.splitext(parsed_url.path)[1]
        tag = "_".join(tags)  # TODO tag 여러 개일때 구조

        # 이미지 파일명 생성
        filename = f"{base_dir}/{tag}_{title}_{idx}.{ext}"
        retry_list = []
        fail_list = []

        # 이미지 다운로드 및 저장
        # TODO request 실패, 에러 시 처리는 실제 동작보고 추가 처리 필요.
        try:
            response = make_requests(
                url=image_url,
                api_proxies=api_proxies,
                method='GET',
                params=None,
                headers=None
            )

            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
            else:
                logs.log_data(
                    f'response error: {response.status_code} - {response.reason}: {response.text}',
                    'warning'
                )
                fail_list.append(image_url)

        except Exception as e:
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code in [403, 429]:
                    retry_list.append(image_url)
                else:
                    retry_list.append(image_url)

            else:
                if isinstance(e, requests.exceptions.ReadTimeout):
                    retry_list.append(image_url)
                elif isinstance(e, requests.exceptions.ProxyError):
                    retry_list.append(image_url)
                else:
                    retry_list.append(image_url)

        # TODO retry 작업

    return {"result": True}