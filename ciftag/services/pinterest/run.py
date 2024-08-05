import os
import time
import json

from playwright.sync_api import sync_playwright

import ciftag.utils.logger as logger
import ciftag.utils.crypto as crypto

from ciftag.services.pinterest import PAGETYPE
from ciftag.services.pinterest.wrapper import execute_with_logging
from ciftag.services.pinterest import (
    login,
    search
)


USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
logs = logger.Logger()  # TODO PAGETYE별로 log 디렉토리 변경?


def run(data: dict, headless: bool = True):
    uid = data['uid']
    passwd = data['passwd']
    tag: str = data['tags'].pop()  # 핀터레스트는 구조 상 단일 태그
    max_pins: int = data['max_pins']  # 큐 올릴 시, 목표하는 갯수를 동시에 실행될 컨테이너 만큼 균등하게 나눠서 올리기
    retry = int(data['retry']) if data.get('retry') else 1

    # 특정 사이즈의 이미지 지정 시
    desired_width = int(data['desired_width']) if data.get('desired_width') else None
    desired_height = int(data.get('desired_height')) if data.get('desired_height') else None

    # TODO 사이즈를 후처리 단계에서 조정 할 시


    if crypto_key := os.getenv('crypto_key'):
        ciftag_crypto = crypto.CiftagCrypto()
        ciftag_crypto.load_key(crypto_key)
        passwd = ciftag_crypto.decrypt_text(passwd)

    # TODO proxy setting
    proxy_settings = {}
    api_proxies = {}

    with sync_playwright() as playwright:
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
        result = execute_with_logging(login.login, context, uid, passwd)

        # try:
        #     result = login.login(logs, context, uid, passwd)
        # except Exception as e:
        #     logs.log_data(f"---{PAGETYPE} 로그인 Error : {e}")
        #     result = {"result": False, "message": "Run Fail"}
        #

        if not result['result']:
            return result

        # 검색 시도
        result = execute_with_logging(
            search.search, logs, result['page'], tag, max_pins, desired_width, desired_height
        )

        # try:
        #     result = search.search(logs, result['page'], max_pins, img_width=None, img_height=None)
        # except Exception as e:
        #     logs.log_data(f"---{PAGETYPE} 검색 Error : {e}")
        #     result = {"result": False, "message": "Run Fail"}

        if not result['result']:
            return result



