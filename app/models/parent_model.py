from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Parent(Base):
    __tablename__ = 'parents'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)

    # Một phụ huynh có nhiều học sinh
    children = relationship("Student", back_populates="parent")

    # Quan hệ one-to-one với User
    user = relationship("User", back_populates="parent", uselist=False)

    def __repr__(self):
        return f"<Parent(user_id={self.user_id})>"
