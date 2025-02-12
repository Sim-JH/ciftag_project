import os
import time
import random
from datetime import datetime
from typing import Any, Dict

from playwright.sync_api import sync_playwright

import ciftag.utils.logger as logger
import ciftag.utils.crypto as crypto
from ciftag.settings import TIMEZONE, SERVER_TYPE
from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.scripts.pinterest import insert_pint_result
from ciftag.services.pinterest import PAGETYPE
from ciftag.services.wrapper import execute_with_logging
from ciftag.services.pinterest import (
    login,
    search,
)


USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"


def run(
        task_id: int,
        cred_info: Dict[str, Any],
        runner_identify: str,
        goal_cnt: int,
        data: Dict[str, Any],
        redis_name: str,
        headless: bool = True
):
    """ 핀터레스트 크롤링 메인 타스크
    :param task_id: 내부 작업 ID
    :param cred_info: 계정 정보
    :param runner_identify: 처리기 식별자
    :param goal_cnt: 목표 수량
    :param data: 메타 데이터
    :param redis_name: redis set name
    :param headless: 헤드리스 모드 여부
    """
    time.sleep(random.randrange(1, 10))
    logs = logger.Logger(log_dir=f'Crawl/{PAGETYPE}/Main', log_name=runner_identify)
    logs.log_data(f'--- 작업 시작 task id: {task_id}')
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.run.name})

    cred_id = cred_info.get('cred_id')
    cred_pw = cred_info.get('cred_pw')
    run_on = data['run_on']
    tag: str = data['tags']  # 핀터레스트는 구조 상 단일 태그

    # pw 암호 키 존재 시
    if crypto_key := os.getenv('crypto_key'):
        ciftag_crypto = crypto.CiftagCrypto()
        ciftag_crypto.load_key(crypto_key.encode())
        cred_pw = ciftag_crypto.decrypt_text(cred_pw)

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

        # 로그인 시도
        if cred_id and cred_pw:
            result = execute_with_logging(login.login, logs, context, task_id, cred_id, cred_pw)
            page = result['page']

            if not result['result']:
                return result
        # 로그인 없이 시도. 현재 API 기반 요청의 경우는 해당 사항 없음
        else:
            page = context.new_page()

        # 태그 기반 원본 페이지 url 크롤링
        result = execute_with_logging(
            search.get_thumbnail_url, logs, task_id, page, redis_name, tag, goal_cnt
        )
        
        if not result['result']:
            return result

        context.close()
        browser.close()

    end_dt = datetime.now(TIMEZONE)
    update_task_status(
        task_id, {'task_sta': enums.TaskStatusCode.parse.name, 'get_cnt': len(result['pins']), 'end_dt': end_dt}
    )
    return {'result': True, 'pins': result['pins']}
