from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, Integer, Date, Enum, Time
from app.database import Base
import enum

class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"

class Attendance(Base):
    __tablename__ = "attendances"

    attendance_id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.schedule_id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False)  

    attendance_date = Column(Date)
    status = Column(Enum(AttendanceStatus))
    checkin_time = Column(Time, nullable=True)

    # Quan hệ với học sinh, lịch trình, lớp
    student = relationship("Student", back_populates="attendances")
    schedule = relationship("Schedule", back_populates="attendances")
    class_ = relationship("Class", back_populates="attendances")  

    def __repr__(self):
        return (
            f"<Attendance(student_user_id={self.student_user_id}, "
            f"schedule_id={self.schedule_id}, class_id={self.class_id}, "
            f"date={self.attendance_date})>"
        )
