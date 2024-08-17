from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from ciftag.settings import TIMEZONE

Base = declarative_base()


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), default=func.now().astimezone(TIMEZONE)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now().astimezone(TIMEZONE),
        onupdate=func.now().astimezone(TIMEZONE)
    )
