import os
import time

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.services.flickr import PAGETYPE

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def login(logs, context, task_id, cred_id, cred_pw):
    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 로그인 시작: {cred_id}')
    # 상태 업데이트
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.login.name})

    # 리소스 최적화를 위해 불필요한 리소스 스킵
    def handle_route(route):
        if route.request.method != "GET":
            if route.request.method == "POST" and route.request.url.find("/signin"):
                route.continue_()
            else:
                route.abort()
        else:
            if route.request.resource_type in ["other", "ping", "font", "media"]:
                route.abort()
            else:
                route.continue_()

    page = context.new_page()

    # 초기 진입 시도 5회 반복 (timeout 에러를 catch 못하는 bug 방지를 위해 스크린샷)
    for _ in range(5):
        try:
            page.route('**/*', handle_route)
            page.goto('https://identity.flickr.com/login')
            time.sleep(5)
            page.screenshot(path=f'{os.path.dirname(logs.log_path)}/flickr_login.png')  # goto timeout 발생 체크
            break
        except Exception as e:
            if isinstance(e, (PlaywrightTimeoutError, TimeoutError)):
                logs.log_data(f'{cred_id} {PAGETYPE} login page Timeout 진입 재시도')
            else:
                logs.log_data(f'{cred_id} {PAGETYPE} login page 진입 재시도: {e}')
            page.close()
            time.sleep(5)
            page = context.new_page()
    else:
        logs.log_data(f'{cred_id} {PAGETYPE} login page 진입 실패')
        return {"result": False, "message": 'Timeout'}

    # 로그인 시도
    page.set_default_timeout(60000)  # 기본 타임 아웃을 60초로 설정
    page.wait_for_selector('input[type="email"]')
    page.type('input[type="email"]', cred_id, delay=200)
    page.click('[data-testid="identity-form-submit-button"]')

    page.wait_for_selector('input[type="password"]')
    page.type('input[type="password"]', cred_pw, delay=200)
    page.click('[data-testid="identity-form-submit-button"]')

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    time.sleep(3)

    logs.log_data(f'{cred_id} {PAGETYPE} 로그인 성공')
    return {"result": True, "page": page}
