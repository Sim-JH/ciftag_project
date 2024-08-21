from enum import Enum


class RunOnCode(Enum):
    """ 실행 환경 코드
    local: 로컬 실행
    aws: 클라우드 실행
    """
    local = "0"
    aws = "1"


class StatusCode(Enum):
    """ 계정 상태 코드
    active: 활성
    pause: 일시 정지 (초기 생성 포함)
    inactive: 비활성
    """
    active = "0"
    pause = "1"
    inactive = "2"


class HistoryCode(Enum):
    """ 계정 히스토리 코드
    create: 생성
    update: 업데이트
    delete: 삭제
    login: 로그인
    """
    create = "0"
    update = "1"
    delete = "2"
    login = "3"


class UserRoleCode(Enum):
    """ 계정 권한 코드
    admin: 관리자
    update: 일반 유저
    """
    admin = "0"
    user = "1"


class CrawlTargetCode(Enum):
    """ 크롤링 목표 사이트
    pinterest: https://www.pinterest.com
    danbooru: https://danbooru.donmai.us/
    """
    pinterest = "1"
    danbooru = "2"


class CrawlStatusCode(Enum):
    """ 크롤링 상태 코드
    load: 실행
    success: 성공
    failed: 실패
    download: 이미지 다운로드
    end: 작업 종료
    """
    load = "0"
    success = "1"
    failed = "2"
    download = "3"
    end = "4"
