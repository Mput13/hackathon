import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from models import Base
from models.core import TimestampMixin


class RequestStatus(enum.Enum):
    SUCCESSFUL = 'successful'
    UNSUCCESSFUL = 'unsuccessful'
    ESCALATION = 'escalation'


class Request(Base, TimestampMixin):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_id = Column(Integer, nullable=True)
    question = Column(String, nullable=False)
    answer = Column(String)
    # name = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(RequestStatus))

    user = relationship("User", back_populates="requests")
