import re
import time

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.integrations.redis import RedisManager
from ciftag.services.pinterest import PAGETYPE


def get_thumbnail_url(logs, task_id, page, redis_name, tag, goal_cnt):
    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 검색 시작: {tag}')
    # 상태 업로드
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.search.name})

    page.goto(f"https://www.pinterest.com/search/pins/?q={tag}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(60000)

    redis_m = RedisManager()
    _continue_flag = True
    pins = []
    last_height = page.evaluate("document.body.scrollHeight")

    while len(pins) < goal_cnt:
        # 새로운 핀 추출
        new_pins = page.evaluate('''() => {
            const pinData = [];
            const pinUrlSet = new Set();
            document.querySelectorAll("div[data-test-id^='pin']").forEach(pin => {
                const img = pin.querySelector("img");
                const link = pin.querySelector("a[href^='/pin/']");
                if (img && link) {
                    const fullLink = "https://www.pinterest.com" + link.getAttribute("href");
                    if (!pinUrlSet.has(fullLink)) {
                        pinData.push([
                            img.alt,
                            img.src,
                            fullLink
                        ]);
                        pinUrlSet.add(fullLink);
                    }
                }
            });
            return pinData;
        }''')

        logs.log_data(f'서치된 핀 갯수: {len(new_pins)}')

        for title, thumbnail_url, link in new_pins:
            if len(pins) >= goal_cnt:
                _continue_flag = False
                break

            # 컨테이너간 중복 체크
            if redis_m.check_and_add_with_lua(redis_name, link):
                # 중복 통과하면 해당 url을 리스트에 추가
                pins.append({
                    "thumbnail_url": thumbnail_url,
                    "title": title,
                    "detail_link": link,
                })
            else:
                continue

        # 할당된 목표 횟수 미도달 시 추가 스크롤
        if _continue_flag:
            page.go_back()
            page.wait_for_load_state("networkidle")
            time.sleep(5)

            # 스크롤을 끝까지 내림
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 스크롤 후 모든 이미지 로딩 확인
            for _ in range(5):
                time.sleep(60)  # 새 콘텐츠 로딩 대기
                all_images_loaded = page.evaluate('''() => {
                    const images = document.querySelectorAll("img");
                    return Array.from(images).every(img => img.complete);
                }''')

                if all_images_loaded:
                    break
            else:
                logs.log_data('Error On Scroll Continue')
                raise Exception('Error On Scroll Continue')

            # 페이지 끝에 도달했는지 확인
            new_height = page.evaluate("document.body.scrollHeight")

            # 마지막 페이지가 아니면 스크롤
            if new_height == last_height:
                logs.log_data(f'마지막 페이지 진입 {new_height} {last_height}')
                break
            else:
                last_height = new_height

    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 검색 종료: {tag}, 검색 갯수: {len(pins)}')

    return {"result": True, "pins": pins}
