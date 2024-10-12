import time
import random
import re

from ciftag.models import enums
from ciftag.scripts.common import update_task_status
from ciftag.integrations.redis import RedisManager
from ciftag.services.tumblr import PAGETYPE


def get_image_width(url):
    _match = re.search(r'(\d+)w', url)
    return int(_match.group(1)) if _match else 0


def search(logs, task_id, page, redis_name, tag, goal_cnt, min_width=None, max_width=None):
    logs.log_data(f'--- Task-{task_id} {PAGETYPE} 검색 시작: {tag}')
    # 상태 업데이트
    update_task_status(task_id, {'task_sta': enums.TaskStatusCode.search.name})

    page.goto(f"https://www.tumblr.com/search/{tag}/photo?src=typed_query&sort=recent")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(60000)

    redis_m = RedisManager()
    _continue_flag = True
    posts = []
    last_height = page.evaluate("document.body.scrollHeight")

    while len(posts) < goal_cnt:
        # 새로운 포스트 추출 (중복 제외) tumblr는 title 요소가 없고 태그가 대체. 태그로 타이틀 대체할지는 고려할 요소
        new_posts = page.evaluate('''() => {
            const postData = [];
            const pinUrlSet = new Set();
            document.querySelectorAll("article").forEach(post => {
                const img = post.querySelector("img");
                const postUrlSet = new Set();

                if (img) {
                    // tumblr 검색은 기본적으로 srcset 단위
                    const srcset = img.getAttribute('srcset');
                    let smallestImage = ''; // 중복체크 및 썸네일
                    
                     if (srcset) {
                        const srcsetUrls = srcset.split(',').map(url => url.trim());
                        smallestImage = srcsetUrls[0].split(' ')[0];
                        
                        if (!postUrlSet.has(smallestImage)) {
                            postData.push([smallestImage, srcsetUrls]);
                            postUrlSet.add(smallestImage);
                        } 
                    }
                }
            });
            return postData;
        }''')

        for thumbnail_url, image_urls in new_posts:
            if len(posts) >= goal_cnt:
                _continue_flag = False
                break

            time.sleep(random.randrange(1, 3))

            # 이미 체크한 link는 pass
            if redis_m.check_set_form_redis(redis_name, thumbnail_url):
                continue

            # 중복 크롤링 방지
            redis_m.add_set_to_redis(redis_name, thumbnail_url)

            try:
                # 최소/최대 이미지 크기 필터링
                if min_width or max_width:
                    valid_image_urls = []
                    for url in image_urls:
                        # URL에서 너비 정보를 추출
                        width_match = re.search(r'(\d+)w', url)

                        if width_match:
                            img_width = int(width_match.group(1))

                            if ((min_width is None or img_width >= min_width) and
                                    (max_width is None or img_width <= max_width)):
                                valid_image_urls.append(url)
                else:
                    valid_image_urls = image_urls

                if not len(valid_image_urls):
                    continue

                # valid_image_urls에서 최대 너비 이미지 선택
                image_url = max(valid_image_urls, key=get_image_width)

                # 선정된 이미지의 너비와 높이 파싱
                size_match = re.search(r'(\d+)x(\d+)', image_url)

                height = int(size_match.group(1)) if size_match else 0
                width = get_image_width(image_url)

                posts.append({
                    "thumbnail_url": thumbnail_url,
                    "image_url": image_url,
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
                break
            else:
                last_height = new_height

    return {"result": True, "posts": posts}
