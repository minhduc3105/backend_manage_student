from sqlalchemy import DECIMAL, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TeacherReview(Base):
    __tablename__ = "teacher_reviews"

    review_id = Column(Integer, primary_key=True, index=True)

    teacher_user_id = Column(Integer, ForeignKey("teachers.user_id", ondelete="CASCADE"), nullable=False)
    student_user_id = Column(Integer, ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)

    rating = Column(DECIMAL(10, 2), nullable=False)
    review_content = Column(String)
    review_date = Column(DateTime, default=datetime.utcnow)

    # Quan hệ với Teacher và Student
    teacher = relationship("Teacher", back_populates="review")
    student = relationship("Student", back_populates="review")

    def __repr__(self):
        return f"<TeacherReview(teacher_user_id={self.teacher_user_id}, student_user_id={self.student_user_id}, rating={self.rating})>"
