import os
import zipfile
from typing import List

from ciftag.exceptions import CiftagAPIException
from ciftag.integrations.redis import RedisManager

# 필요 시 env로 이동
RATE_LIMIT = 3  # 허용할 최대 요청 수
RATE_LIMIT_WINDOW = 10  # 제한 시간 (초)


def limit_request(user_pk: str):
    """동일 사용자에 대한 요청 제한 설정"""
    redis_m = RedisManager()
    key = f"crawl_request:{user_pk}"
    # 사용자 요청 수 증가
    request_count = redis_m.increase_key(key)
    print(request_count)

    # 처음 요청일 경우, 만료 시간 설정
    if request_count == 1:
        redis_m.set_expire(key, RATE_LIMIT_WINDOW)

    # 요청 수가 제한을 넘었을 경우
    if request_count > RATE_LIMIT:
        ttl = redis_m.get_ttl(key)
        raise CiftagAPIException(message=f"Too many requests. Please try again {ttl} second later.", status_code=429)


def provide_to_zipfile(zip_path: str, image_path_list: List[str]):
    # Zip 파일 생성
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for path in image_path_list:
            zipf.write(path, os.path.basename(path))

    return zip_path


def remove_file(filepath: str):
    try:
        os.remove(filepath)
    except OSError as e:
        print(f"Error: {filepath} : {e.strerror}")
