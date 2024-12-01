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
from ciftag.scripts.common import update_sub_task_status
from ciftag.scripts.pinterest import insert_pint_result
from ciftag.services.pinterest import PAGETYPE
from ciftag.services.wrapper import execute_with_logging
from ciftag.services.pinterest import (
    detail
)

USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"


def run(
        sub_task_id: int,
        info_id: int,
        runner_identify: str,
        goal_cnt: int,
        data: Dict[str, Any],
        headless: bool = True
):
    """ 핀터레스트 크롤링 서브 타스크
    :param sub_task_id: 세부 작업 ID
    :param info_id: 수행 정보 ID
    :param runner_identify: 처리기 식별자
    :param goal_cnt: 목표 수량
    :param data: 메타 데이터
    :param headless: 헤드리스 모드 여부
    """
    time.sleep(random.randrange(1, 10))
    start_time = time.time()
    logs = logger.Logger(log_dir=f"Crawl/{PAGETYPE}/Sub", log_name=runner_identify)
    update_sub_task_status(sub_task_id, {'task_sta': enums.TaskStatusCode.run.name})
    logs.log_data(f'--- 작업 시작 task id: {sub_task_id}')

    run_on = data['run_on']
    pins = data['pins']

    # 이미지 크기 범위 지정 시
    min_width = int(data['min_width']) if int(data.get('min_width')) else None
    max_width = int(data.get('max_width')) if int(data.get('max_width')) else None

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

        page = context.new_page()

        # 원본 페이지 기반 이미지 url 크롤링
        result = execute_with_logging(
            detail.get_origin_url, logs, sub_task_id, pins, page, min_width, max_width
        )

        if not result['result']:
            return result

        context.close()
        browser.close()

    # 결과 적재
    pins = result['pins']
    logs.log_data(f'--- Task-{sub_task_id} {PAGETYPE} 결과 적재')

    for pin in pins:
        pin.update({
            'pint_pk': info_id,
            'run_on': run_on['name'],
            'download': False
        })

        insert_pint_result(pin)

    end_dt = datetime.now(TIMEZONE)
    elapsed_time = time.time() - start_time
    update_sub_task_status(
        sub_task_id, {'task_sta': enums.TaskStatusCode.success.name, 'get_cnt': len(pins), 'end_dt': end_dt}
    )

    return {'result': True, 'hits': len(pins), 'elapsed_time': elapsed_time, 'end_dt': end_dt}
