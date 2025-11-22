from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.user_model import User
# Import mô hình Test để thiết lập mối quan hệ
from app.models.test_model import Test
from app.models.class_model import Class
from app.models.evaluation_model import Evaluation
from app.models.payroll_model import Payroll
from app.models.teacher_review_model import TeacherReview

class Teacher(Base):
    """
    Model cho bảng teachers.
    """
    __tablename__ = 'teachers'
    # user_id là khóa chính và khóa ngoại
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True, unique=True, nullable=False)
    base_salary_per_class = Column(Float, nullable=False, default=0.0)
    reward_bonus = Column(Float, nullable=False, default=0.0)


    # Mối quan hệ với người dùng (one-to-one)
    user = relationship("User", back_populates="teacher")

    # Mối quan hệ với lớp học (one-to-many)
    classes = relationship("Class", back_populates="teacher")

    # Mối quan hệ với đánh giá (one-to-many)
    evaluations = relationship("Evaluation", back_populates="teacher")
    
    # Mối quan hệ one-to-many với Test
    tests = relationship("Test", back_populates="teacher")

    # Mối quan hệ one-to-one với Payroll
    payroll = relationship("Payroll", uselist=False, back_populates="teacher")

    # Mối quan hệ one-to-one với TeacherReview
    review = relationship("TeacherReview", uselist=False, back_populates="teacher")

    def __repr__(self):
        return f"<Teacher(user_id='{self.user_id}')>"
