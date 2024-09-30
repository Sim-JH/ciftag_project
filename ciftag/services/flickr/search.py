import time
import random
import re

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.integrations.redis import RedisManager
from ciftag.services.flickr import PAGETYPE


def get_image_width(url):
    _match = re.search(r'(\d+)w', url)
    return int(_match.group(1)) if _match else 0


def search(logs, task_id, page, redis_name, tag_list, goal_cnt, min_width=None, max_width=None):
    tags = "+".join(tag_list)
    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 검색 시작: {tags}')
    # 상태 업데이트
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.search.name})

    # flickr는 초기 이미지가 많은 편
    page.set_default_timeout(60000*3)  # 기본 타임 아웃을 3분으로 설정
    page.goto(f"https://www.flickr.com/search/?text={tags}")
    page.wait_for_load_state("networkidle", timeout=60000*3)
    page.wait_for_timeout(60000)

    redis_m = RedisManager()
    _continue_flag = True
    photos = []
    last_height = page.evaluate("document.body.scrollHeight")

    while len(photos) < goal_cnt:
        # 새로운 핀 추출 (중복 제외)
        new_photos = page.evaluate('''() => {
            const photoData = [];
            const photoUrlSet = new Set();
            
            // div class 형식이므로 div[] -> div.
            document.querySelectorAll("div.photo-list-photo-view").forEach(view => {
                const img = view.querySelector("img");
                const interaction = view.querySelector("div.photo-list-photo-interaction").querySelector("a.overlay");
                
                if (img && interaction) {
                    let imageUrl = img.getAttribute('src');
                    const fullLink  = "https://www.flickr.com" + interaction.getAttribute("href");
                    
                    if (!imageUrl.startsWith('http')) {
                        imageUrl = 'https:' + imageUrl;
                    }
                    
                    if (!photoUrlSet.has(fullLink)) {
                        photoData.push([
                            imageUrl,
                            fullLink
                        ]);
                        photoUrlSet.add(fullLink);
                    }
                }
            });
            return photoData;
        }''')

        for thumbnail_url, link in new_photos:
            if len(photos) >= goal_cnt:
                _continue_flag = False
                break

            time.sleep(random.randrange(1, 3))
            # 이미 체크한 link는 pass
            if redis_m.check_set_form_redis(redis_name, link):
                continue

            # 중복 크롤링 방지
            redis_m.add_set_to_redis(redis_name, link)

            try:
                # 상세 페이지로 이동하여 원본 이미지 URL 추출
                page.goto(link)
                page.wait_for_load_state('domcontentloaded')
                page.wait_for_selector("img.main-photo[src]")
                time.sleep(3)

                img_element = page.query_selector("img.main-photo")

                if img_element is None:
                    continue

                # flickr는 src만 제공
                image_url = img_element.get_attribute("src")
                # element에서 아래 내용 제공
                title = img_element.get_attribute("alt")
                height = img_element.get_attribute("height")
                width = img_element.get_attribute("width")

                if not image_url.startswith("http"):
                    image_url = "https:" + image_url

                # 최소/최대 이미지 크기 필터링
                if min_width or max_width:
                    if ((min_width is None or width >= min_width) and
                            (max_width is None or width <= max_width)):
                        continue

                photos.append({
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

            # 페이지 끝에 도달했는지 확인
            new_height = page.evaluate("document.body.scrollHeight")

            # 마지막 페이지가 아니면 스크롤
            if new_height == last_height:
                break
            else:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(60)  # 새 콘텐츠 로딩 대기
                last_height = new_height

    return {"result": True, "photos": photos}


