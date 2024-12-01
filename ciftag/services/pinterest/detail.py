import time
import random
import re

from ciftag.models import enums
from ciftag.scripts.common import update_sub_task_status
from ciftag.services.pinterest import PAGETYPE

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def get_image_width(url):
    _match = re.search(r'/(\d+)x(\d+)/', url)
    return int(_match.group(1)) if _match else 0


def get_origin_url(logs, sub_task_id, pins, page, min_width=None, max_width=None):
    logs.log_data(f'--- Task-{sub_task_id} {PAGETYPE} 원본 이미지 크롤링 시작')
    # 상태 업로드
    update_sub_task_status(sub_task_id, {'task_sta': enums.TaskStatusCode.parse.name})
    origin_pins = []

    for title, thumbnail_url, link in pins:
        try:
            # 타임아웃 발생 시 최대 3회 새로고침 시도
            for _ in range(3):
                # 상세 페이지로 이동하여 원본 이미지 URL 추출
                try:
                    page.goto(link)
                    page.wait_for_load_state('domcontentloaded')
                    page.wait_for_selector("img[src], img[srcset]", timeout=60000 * 2)
                    time.sleep(3)
                    break
                except (PlaywrightTimeoutError, TimeoutError):
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

            origin_pins.append({
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

    logs.log_data(f'--- Task-{sub_task_id} {PAGETYPE} 원본 크롤링 종료')

    return {"result": True, "pins": origin_pins}
