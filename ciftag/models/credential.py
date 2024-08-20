from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum

from ciftag.models.base import Base, TimestampMixin
from ciftag.models.enums import CrawlTargetCode, StatusCode


# 인증 정보 관련
class CredentialInfo(Base, TimestampMixin):
    """로그인 인증 정보"""

    __tablename__ = "cred_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    cred_id = Column(String)  # 인증 ID
    cred_pw = Column(String)  # 인증 PW
    target_code = Column(Enum(CrawlTargetCode))  # 대상 사이트 코드
    status_code = Column(Enum(StatusCode))  # 계정 상태 코드
    last_connected_at = Column(DateTime(timezone=True), nullable=True, default=TimestampMixin.created_at.default.arg)  # 마지막 접속
    etc = Column(String, nullable=True)

