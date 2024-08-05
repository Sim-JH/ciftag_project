import time

from ciftag.services.pinterest import PAGETYPE


def login(logs, context, uid, passwd):
    logs.log_data(f'--- {PAGETYPE} 로그인 시작: {uid}')
    dir_path = f""

    # 리소스 최적화를 위해 login 관련 요청에 대해서만 진행
    def handle_route(route):
        if route.request.method != "GET":
            if route.request.method == "POST" and route.request.url.find("/login"):
                route.continue_()
            else:
                route.abort()
        else:
            if route.request.resource_type == "image" \
                    or route.request.resource_type == "stylesheet" \
                    or route.request.resource_type == "other" \
                    or route.request.resource_type == "ping" \
                    or route.request.resource_type == "font" \
                    or route.request.resource_type == "media":
                route.abort()
            else:
                # print(route.request.resource_type)
                route.continue_()

    page = context.new_page()

    # 초기 진입 진입 시도 5회 반복 (timeout 에러를 catch 못하는 bug 방지를 위해 스크린샷)
    for _ in range(5):
        try:
            page.route('**/*', handle_route)
            page.goto('https://www.pinterest.com/login/')
            time.sleep(5)
            page.screenshot(path=f'{logs.log_path}/goto_tmp.png')  # goto timeout 발생 체크
            break
        except Exception as e:
            if isinstance(e, TimeoutError):
                logs.log_data(f'{uid} {PAGETYPE} login page Timeout 진입 재시도')
            else:
                logs.log_data(f'{uid} {PAGETYPE} login page 진입 재시도: {e}')
            page.close()
            time.sleep(5)
            page = context.new_page()
    else:
        logs.log_data(f'{uid} {PAGETYPE} login page 진입 실패')
        return {"result": False, "message": 'Timeout'}

    # 로그인 시도
    page.fill('input[id="email"]', uid, delay=200)
    page.fill('input[id="password"]', passwd, delay=200)
    page.click('button[type="submit"]')

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    return {"result": True, "page": page}
