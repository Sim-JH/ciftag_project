from enum import Enum


class RunOnCode(Enum):
    """실행 환경 코드"""
    local = "0"  # 로컬 실행
    aws = "1"  # 클라우드 실행


class StatusCode(Enum):
    """계정 상태 코드"""
    active = "0"  # 활성
    pause = "1"  # 일시 정지 (초기 생성 포함)
    inactive = "2"  # 비활성


class UserHistoryCode(Enum):
    """계정 히스토리 코드"""
    create = "0"  # 생성
    update = "1"  # 업데이트
    delete = "2"  # 삭제
    login = "3"  # 로그인


class UserRoleCode(Enum):
    """계정 권한 코드"""
    admin = "0"  # 관리자
    user = "1"  # 일반 유저


class CrawlTargetCode(Enum):
    """크롤링 목표 사이트"""
    pinterest = "1"  # https://www.pinterest.com
    tumblr = "2"  # https://www.tumblr.com
    flickr = "3"  # https://www.flickr.com


class CrawlStatusCode(Enum):
    """내부 작업 상태 코드"""
    load = "0"  # 실행
    success = "1"  # 성공
    failed = "2"  # 실패
    download = "3"  # 이미지 다운로드
    end = "4"  # 작업 종료


class WorkStatusCode(Enum):
    """외부 작업 상태 코드"""
    # 작업 실행 관련
    pending = "100"  # 대기
    trigger = "110"  # 트리거 (push queue)
    postproc = "120"  # 실제 이미지 저장
    download = "130"  # 후처리

    # 작업 완료 관련
    success = "202"  # 크롤링 작업 성공
    end = "200"  # 모든 작업 종료

    # 작업 에러 관련
    failed = "400"  # 작업 실패
    canceled = "401"  # 작업 취소


class WorkTypeCode(Enum):
    """작업 구분 코드"""
    crawl = "1"  # 크롤링
    download = "2"  # 다운로드


class TaskStatusCode(Enum):
    """내부 작업 상태 코드"""
    # 작업 실행 관련
    load = "100"  # 대기 (pop queue)
    run = "110"  # 수집 시작
    login = "120"  # 로그인
    search = "130"  # 태그 검색
    parse = "140"  # 이미지 url 가져오기
    result = "150"  # 결과 인입

    # 작업 완료 관련
    success = "200"  # 작업 성공

    # 작업 에러 관련
    failed = "400"  # 작업 실패
    canceled = "401"  # 작업 취소
    retry = "402"  # 작업 재시도
