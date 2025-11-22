# app/models/manager_model.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.user_model import User


class Manager(Base):
    """
    Model cho bảng managers.
    """
    __tablename__ = 'managers'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)

    # Mối quan hệ với người dùng (one-to-one)
    user = relationship("User", back_populates="manager", uselist=False)

    def __repr__(self):
        return f"<Manager(user_id={self.user_id})>"
