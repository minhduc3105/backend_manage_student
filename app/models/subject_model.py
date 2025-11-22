# app/models/subject.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
# Import mô hình Test để thiết lập mối quan hệ
from app.models.test_model import Test

class Subject(Base):
    """
    Model cho bảng subjects.
    """
    __tablename__ = 'subjects'
    subject_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    classes = relationship("Class", back_populates="subject")
    
    # Thêm mối quan hệ mới với bảng Test
    ##tests = relationship("Test", back_populates="subject")

    def __repr__(self):
        return f"<Subject(name='{self.name}')>"
