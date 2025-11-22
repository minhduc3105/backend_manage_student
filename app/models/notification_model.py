# app/models/notification_model.py
from sqlalchemy import Boolean, Column, Integer, ForeignKey, DateTime, Text, func, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class NotificationType(str, enum.Enum):
    """Định nghĩa các loại thông báo."""
    payroll = "payroll"
    tuition = "tuition"
    schedule = "schedule"
    warning = "warning"
    others = "others" 
    

class Notification(Base):
    """
    Model cho bảng notifications.
    """
    __tablename__ = 'notifications'
    notification_id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.user_id'))
    receiver_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=func.now())
    type = Column(Enum(NotificationType), nullable=False)
    is_read = Column(Boolean, default=False)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])