import os
import time

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.services.tumblr import PAGETYPE


def login(logs, context, task_id, cred_id, cred_pw):
    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 로그인 시작: {cred_id}')
    # 상태 업로드
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.login.name})

    # 리소스 최적화를 위해 불필요한 리소스 스킵
    def handle_route(route):
        if route.request.method != "GET":
            if route.request.method == "POST" and route.request.url.find("/login"):
                route.continue_()
            else:
                route.abort()
        else:
            if route.request.resource_type == "other" \
                    or route.request.resource_type == "ping" \
                    or route.request.resource_type == "font" \
                    or route.request.resource_type == "media":
                route.abort()
            else:
                route.continue_()

    page = context.new_page()

    # 초기 진입 진입 시도 5회 반복 (timeout 에러를 catch 못하는 bug 방지를 위해 스크린샷)
    for _ in range(5):
        try:
            page.route('**/*', handle_route)
            page.goto('https://www.tumblr.com/login/')
            time.sleep(5)
            page.screenshot(path=f'{os.path.dirname(logs.log_path)}/goto_tmp.png')  # goto timeout 발생 체크
            break
        except Exception as e:
            if isinstance(e, TimeoutError):
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
    page.click('text="Log in"')

    page.wait_for_selector('input[name="email"]')
    page.type('input[name="email"]', cred_id, delay=200)
    page.type('input[name="password"]', cred_pw, delay=200)
    page.click('button[type="submit"]')

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    time.sleep(3)

    return {"result": True, "page": page}
