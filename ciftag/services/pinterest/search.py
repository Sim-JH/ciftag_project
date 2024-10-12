import time
import random
import re

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.integrations.redis import RedisManager
from ciftag.services.pinterest import PAGETYPE


def get_image_width(url):
    _match = re.search(r'/(\d+)x(\d+)/', url)
    return int(_match.group(1)) if _match else 0


def search(logs, task_id, page, redis_name, tag, goal_cnt, min_width=None, max_width=None):
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
        # 새로운 핀 추출 (중복 제외)
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

        logs.log_data(f'서치된 핀 갯수: {len(new_pins)}', )

        for title, thumbnail_url, link in new_pins:
            if len(pins) >= goal_cnt:
                _continue_flag = False
                break

            time.sleep(random.randrange(1, 3))
            # 이미 체크한 link는 pass
            if redis_m.check_set_form_redis(redis_name, link):
                continue

            # 중복 크롤링 방지
            redis_m.add_set_to_redis(redis_name, link)

            try:
                # 타임아웃 발생 시 최대 3회 새로고침 시도
                for _ in range(3):
                    # 상세 페이지로 이동하여 원본 이미지 URL 추출
                    try:
                        page.goto(link)
                        page.wait_for_load_state('domcontentloaded')
                        page.wait_for_selector("img[src], img[srcset]", timeout=60000*2)
                        time.sleep(3)
                        break
                    except TimeoutError:
                        page.reload()
                else:
                    logs.log_data(f"{link} Element not found, continuing execution")
                    continue

                original_img_element = page.query_selector("img[src], img[srcset]")

                if original_img_element is None:
                    continue

                # 크기별 이미지 셋 존재 시 해당 set 사용. 없을 시 단일 src
                src_set = original_img_element.get_attribute("srcset")
                if not src_set:
                    src_set = original_img_element.get_attribute("src")
                    if not src_set:
                        raise ValueError("src_set Not Found")

                image_urls = [url.split(" ")[0] for url in src_set.split(",")]

                # 최소/최대 이미지 크기 필터링
                if min_width or max_width:
                    valid_image_urls = []
                    for url in image_urls:
                        # 이미지 URL에서 크기 정보 추출
                        size_match = re.search(r'/(\d+)x(\d+)/', url)

                        if size_match:
                            img_width = int(size_match.group(1))

                            if ((min_width is None or img_width >= min_width) and
                                    (max_width is None or img_width <= max_width)):
                                valid_image_urls.append(url)
                else:
                    valid_image_urls = image_urls

                if not len(valid_image_urls):
                    continue

                # valid_image_urls에서 최대 너비 이미지 선택 (736x같은 형식으로 표기)
                image_url = max(valid_image_urls, key=get_image_width)
                # 선정된 이미지의 너비와 높이 파싱 (핀터레스트 url에는 너비만 표시되므로 natural로 파싱)
                img_dimensions = page.evaluate('''(image_url) => {
                    return new Promise((resolve, reject) => {
                        const img = new Image();
                        img.onload = () => {
                            resolve({
                                width: img.naturalWidth,
                                height: img.naturalHeight
                            });
                        };
                        img.onerror = reject;
                        img.src = image_url;
                    });
                }''', image_url)

                height = img_dimensions['height']
                width = img_dimensions['width']

                pins.append({
                    "thumbnail_url": thumbnail_url,
                    "image_url": image_url,
                    "title": title,
                    "detail_link": link,
                    "height": height,
                    "width": width,
                })

            except Exception as e:
                logs.log_data(f'Error On Searching Continue: {e}')
                continue

            finally:
                time.sleep(random.randrange(1, 3))

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


