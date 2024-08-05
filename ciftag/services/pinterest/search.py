import time
import re

from ciftag.services.pinterest import PAGETYPE


def search(logs, page, tag, max_pins, desired_width=None, desired_height=None):
    logs.log_data(f'--- {PAGETYPE} 검색 시작: {tag}')
    page.goto(f"https://www.pinterest.com/search/pins/?q={tag}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    pins = []
    last_height = page.evaluate("document.body.scrollHeight")

    while len(pins) < max_pins:
        # 페이지 스크롤
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)  # 새 콘텐츠 로딩 대기

        # 새로운 핀 추출
        new_pins = page.query_selector_all("div[data-test-id^='pin']")

        for pin in new_pins:
            if len(pins) >= max_pins:
                break

            try:
                image_url = pin.query_selector("img").get_attribute("src")

                # 이미지 URL에서 크기 정보 추출
                size_match = re.search(r'/(\d+)x(\d+)/', image_url)
                img_width, img_height = map(int, size_match.groups()) if size_match else None

                title = pin.query_selector("a[title]").get_attribute("title")
                link = "https://www.pinterest.com" + pin.query_selector("a[href^='/pin/']").get_attribute("href")

                # 사이즈 필터링 시
                if desired_width and desired_width != img_width:
                    continue

                if desired_height and desired_height != img_height:
                    continue

                pins.append({
                    "image_url": image_url,
                    "title": title,
                    "link": link,
                    "img_width": img_width,
                    "img_height": img_height
                })
            except AttributeError:
                continue  # 일부 핀에서 정보를 추출할 수 없는 경우 건너뛰기

        # 페이지 끝에 도달했는지 확인
        new_height = page.evaluate("document.body.scrollHeight")

        if new_height == last_height:
            break

        last_height = new_height

    return {"result": True, "pins": pins}
