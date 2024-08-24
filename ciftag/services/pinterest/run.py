import os
import time
import json
import traceback
from typing import Any, Dict, Union

from playwright.sync_api import sync_playwright

import ciftag.utils.logger as logger
import ciftag.utils.crypto as crypto
from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.services.pinterest import PAGETYPE
from ciftag.services.pinterest.wrapper import execute_with_logging
from ciftag.services.pinterest import (
    login,
    search,
    download
)


USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
logs = logger.Logger(log_dir=PAGETYPE)


def run(
        task_id: int,
        work_id: int,
        cred_info: Dict[str, Any],
        runner_identify: str,
        goal_cnt: int,
        data: Dict[str, Any],
        headless: bool = True
):
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.run})

    cred_id = data['cred_id']
    cred_pw = data['cred_pw']
    tag: str = data['tags'].pop()  # 핀터레스트는 구조 상 단일 태그
    max_pins: int = int(data['max_pins'])  # 큐 올릴 시, 목표하는 갯수를 동시에 실행될 컨테이너 만큼 균등하게 나눠서 올리기
    retry = int(data['retry']) if data.get('retry') else 1

    # 이미지 크기 범위 지정 시
    min_width = int(data['min_width']) if data.get('min_width') else None
    max_width = int(data.get('max_width')) if data.get('max_width') else None

    # redis set name
    redis_name = f"{PAGETYPE}_{work_id}"

    # pw 암호 키 존재 시
    if crypto_key := os.getenv('crypto_key'):
        ciftag_crypto = crypto.CiftagCrypto()
        ciftag_crypto.load_key(crypto_key)
        passwd = ciftag_crypto.decrypt_text(cred_pw)

    # TODO proxy setting
    proxy_settings = {}
    api_proxies = {}

    with sync_playwright() as playwright:
        try:
            if len(proxy_settings) > 0:
                browser = playwright.chromium.launch(headless=headless, proxy=proxy_settings)
            else:
                browser = playwright.chromium.launch(headless=headless)

            if headless:
                context = browser.new_context(user_agent=USERAGENT)
            else:
                context = browser.new_context()

            api_context = context.request

            # 로그인 시도
            result = execute_with_logging(login.login, logs, context, cred_id, cred_pw)

            if not result['result']:
                return result

            # 이미지 리스트 추출
            result = execute_with_logging(
                search.search, logs, result['page'], redis_name, tag, max_pins, min_width, max_width
            )

            if not result['result']:
                return result

            result = execute_with_logging(
                download.download_images, logs, result['pins'], cred_id, tag, api_proxies, ext='png'
            )

            # TODO celery/container 에서 모든 작업 끝난 후 할 것들
            # redis set 체크
            # 후처리용 로그

        except Exception as e:
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            logs.log_data(f"--- {PAGETYPE} Exception: {cred_id} {traceback_str}")
