"""작업 로그 관련 된 필드는 외부 키로 사용시 간접적으로만 사용"""
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum, UniqueConstraint

from ciftag.settings import TIMEZONE
from ciftag.models import enums
from ciftag.models.base import Base


class ImageTagMeta(Base):
    """이미지 태그 메타 데이터"""

    __tablename__ = "img_tag_meta"

    id = Column(Integer, primary_key=True)
    data_pk = Column(Integer)  # 대상 데이터 테이블 ID (FK)
    target_code = Column(Enum(enums.CrawlTargetCode))  # 대상 사이트 코드
    description = Column(String)  # 이미지 설명


class ImageMatch(Base):
    """이미지 필터링 매치 테이블 (다운로드 완료한 이미지 대상)"""

    __tablename__ = "img_match"

    id = Column(Integer, primary_key=True)
    data_pk = Column(Integer)  # 대상 데이터 테이블 ID (FK)
    target_code = Column(Enum(enums.CrawlTargetCode))  # 대상 사이트 코드
    filter_dict = Column(JSONB)  # 통과한 필터링 목록  {필터 명칭: threshold}

    __table_args__ = (UniqueConstraint('data_pk', 'target_code', name='img_match_unique'),)
