from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Class(Base):
    __tablename__ = 'classes'

    class_id = Column(Integer, primary_key=True)
    class_name = Column(String(50), unique=True, nullable=False)

    teacher_user_id = Column(Integer, ForeignKey('teachers.user_id', ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False)
    capacity = Column(Integer, nullable=False)
    class_size = Column(Integer, nullable=False, default=0)
    fee = Column(Integer, nullable=False)

    # Quan hệ với Teacher và Subject
    teacher = relationship("Teacher", back_populates="classes")
    subject = relationship("Subject", back_populates="classes")


    # Quan hệ 1-n nhiều với Enrollment, Schedule, Test
    enrollments = relationship(
        "Enrollment",
        back_populates="class_obj",
        cascade="all, delete-orphan"
    )
    schedules = relationship(
        "Schedule",
        back_populates="class_info",
        cascade="all, delete-orphan"
    )
    tests = relationship(
        "Test",
        back_populates="class_rel",
        cascade="all, delete-orphan"
    )

    evaluations = relationship(  
        "Evaluation",
        back_populates="class_",
        cascade="all, delete-orphan"
    )

    attendances = relationship(  
        "Attendance",
        back_populates="class_",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Class(name='{self.class_name}')>"
