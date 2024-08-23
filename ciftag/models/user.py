from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum

from ciftag.models.base import Base, TimestampMixin
from ciftag.models.enums import UserRoleCode, StatusCode, UserHistoryCode


# 로그인 기능은 현재 껍데기만 구현
class UserInfo(Base, TimestampMixin):
    """사용자 정보"""

    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_id = Column(String, unique=True)  # 사용자 ID
    user_pw = Column(String)  # 사용자 PW
    user_name = Column(String)  # 사용자 이름
    auth_code = Column(Enum(UserRoleCode))  # 사용자 권한 코드
    status_code = Column(Enum(StatusCode))  # 계정 상태 코드
    last_connected_at = Column(DateTime(timezone=True), nullable=True)  # 마지막 접속
    etc = Column(String, nullable=True)


class UserHistClass(Base, TimestampMixin):
    """사용자 이력 관리"""

    __tablename__ = "user_info_hist"

    id = Column(Integer, primary_key=True)  # 인덱스
    user_pk = Column(
        Integer,
        ForeignKey("user_info.id", onupdate="CASCADE"),
    )  # 사용자 정보 ID (FK)
    user_id = Column(String, unique=True)  # 사용자 ID
    user_pw = Column(String)  # 사용자 PW
    user_name = Column(String)  # 사용자 이름
    auth_code = Column(Enum(UserRoleCode))  # 사용자 권한 코드
    status_code = Column(Enum(StatusCode))  # 계정 상태 코드
    hist_code = Column(Enum(UserHistoryCode))  # 이력 코드
    etc = Column(String, nullable=True)
