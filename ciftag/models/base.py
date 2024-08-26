from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base

from ciftag.settings import TIMEZONE
from ciftag.models import enums

Base = declarative_base()


class TimestampMixin:
    """시간 데이터 기본 폼"""
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(TIMEZONE)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(TIMEZONE),
        onupdate=lambda: datetime.now(TIMEZONE)
    )


class ImgDataImgDataMixin(TimestampMixin):
    """이미지 데이터 기본 폼
    경로는 local/aws로 download한 이미지들을 통합 보관하는 최종 경로
    """
    run_on = Column(Enum(enums.RunOnCode))  # 수행한 환경
    height = Column(Integer)  # 이미지 높이
    width = Column(Integer)  # 이미지 너비
    thumbnail_path = Column(String, nullable=True)  # 썸네일 경로
    img_path = Column(String, nullable=True)  # 이미지 경로
    size = Column(String, nullable=True)  # 파일 사이즈 (Byte)
    download = Column(Boolean, default=False)  # 실제 다운로드 여부


class CrawlInfoDataMixin(TimestampMixin):
    """크롤링 데이터 기본 폼"""
    run_on = Column(Enum(enums.RunOnCode))  # 수행한 환경
    tags = Column(String)  # 크롤링 대상 태그 tag/tag/tag 구조
    cnt = Column(Integer)  # 목표 이미지 갯수
