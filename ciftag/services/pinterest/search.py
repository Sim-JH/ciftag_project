import time
import re
import traceback

from ciftag.integrations.redis import RedisManager
from ciftag.services.pinterest import PAGETYPE


def get_image_width(url):
    _match = re.search(r'/(\d+)x(\d+)/', url)
    return int(_match.group(1)) if _match else 0


def search(logs, page, redis_name, tag, max_pins, min_width=None, max_width=None):
    logs.log_data(f'--- {PAGETYPE} 검색 시작: {tag}')
    page.goto(f"https://www.pinterest.com/search/pins/?q={tag}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3*600)

    redis_m = RedisManager()
    _continue_flag = True
    pins = []
    last_height = page.evaluate("document.body.scrollHeight")

    while len(pins) < max_pins:
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

        for title, thumbnail_url, link in new_pins:
            if len(pins) >= max_pins:
                _continue_flag = False
                break

            # 이미 크롤링 된 link는 pass
            if redis_m.check_set_form_redis(work_identity, link):
                continue

            try:
                # 상세 페이지로 이동하여 원본 이미지 URL 추출
                page.goto(link)
                page.wait_for_load_state('domcontentloaded')
                page.wait_for_selector("img[src], img[srcset]")
                time.sleep(10)

                original_img_element = page.query_selector("img[src], img[srcset]")

                if original_img_element is None:
                    continue

                # 크기별 이미지 셋 존재 시 해당 set 사용. 없을 시 단일 src
                src_set = original_img_element.get_attribute("srcset")
                if not src_set:
                    src_set = original_img_element.get_attribute("src")

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

                img_width = img_dimensions['width']
                img_height = img_dimensions['height']

                pins.append({
                    "thumbnail_url": thumbnail_url,
                    "image_url": image_url,
                    "title": title,
                    "detail_link": link,
                    "img_width": img_width,
                    "img_height": img_height
                })

                # 중복 크롤링 방지
                redis_m.add_set_to_redis(redis_name, link)

            except Exception as e:
                traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                print(f'Error: {e} {traceback_str}')
                continue

            finally:
                time.sleep(10)

        if _continue_flag:
            page.go_back()
            page.wait_for_load_state("networkidle")
            time.sleep(5)

            # 페이지 끝에 도달했는지 확인 # TODO 마지막 페이지 확인 방식 개선 필요 [max pins에 충족되도록/더불어 중복 크롤링도 해결필요(redis고려)]
            new_height = page.evaluate("document.body.scrollHeight")

            # 마지막 페이지가 아니면 스크롤
            if new_height == last_height:
                break
            else:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2*60)  # 새 콘텐츠 로딩 대기
                last_height = new_height

    return {"result": True, "pins": pins}


