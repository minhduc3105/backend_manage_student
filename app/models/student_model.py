from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

# Nhập tất cả các mô hình liên quan để SQLAlchemy có thể thiết lập mối quan hệ
from app.models.test_model import Test
from app.models.user_model import User
from app.models.parent_model import Parent
from app.models.class_model import Class
from app.models.tuition_model import Tuition
from app.models.attendance_model import Attendance
from app.models.evaluation_model import Evaluation
from app.models.enrollment_model import Enrollment
from app.models.teacher_review_model import TeacherReview

class Student(Base):
    """
    Model cho bảng students.
    """
    __tablename__ = 'students'

    # user_id là khóa chính và khóa ngoại
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True, unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("parents.user_id"), nullable=True)
    
    # One-to-many với Parent
    parent = relationship("Parent", back_populates="children")


    # Các mối quan hệ 
    tests = relationship("Test", back_populates="student")
    tuitions = relationship("Tuition", back_populates="student")
    enrollments = relationship("Enrollment", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    evaluations = relationship("Evaluation", back_populates="student")
    user = relationship("User", back_populates="student")
    review = relationship("TeacherReview", uselist=False, back_populates="student")

    def __repr__(self):
        return f"<Student(user_id='{self.user_id}')>"
