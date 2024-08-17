from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum

from ciftag.models.base import Base, TimestampMixin
from ciftag.models.enums import UserRole, StatusCode, HistoryCode


# 로그인 기능은 현재 껍데기만 구현
class UserInfo(Base, TimestampMixin):
    """사용자 정보"""

    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_id = Column(String, unique=True)  # 사용자 ID
    user_pw = Column(String)  # 사용자 PW
    user_name = Column(String)  # 사용자 이름
    auth = Column(Enum(UserRole))  # 사용자 권한
    status = Column(Enum(StatusCode))  # 사용자 권한
    last_connected_at = Column(DateTime(timezone=True), nullable=True, default=TimestampMixin.created_at.default.arg)  # 마지막 접속
    etc = Column(String, nullable=True)


class UserHistClass(Base, TimestampMixin):
    """사용자 이력 관리"""

    __tablename__ = "user_info_hist"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    hist_cd = Column(Enum(HistoryCode))  # 이력 코드
    etc = Column(String, nullable=True)