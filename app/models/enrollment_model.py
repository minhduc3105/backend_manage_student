from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# Enum trạng thái enrollment
class EnrollmentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False)

    enrollment_date = Column(Date, default=lambda: datetime.utcnow().date(), nullable=False)

    enrollment_status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.active, nullable=False)

    # Quan hệ với Student và Class
    student = relationship("Student", back_populates="enrollments")
    class_obj = relationship("Class", back_populates="enrollments")

    def __repr__(self):
        return f"<Enrollment(student_user_id={self.student_user_id}, class_id={self.class_id}, status={self.enrollment_status})>"
