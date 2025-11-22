from enum import Enum
from sqlalchemy import Column, Integer, Date, ForeignKey, Text, Enum as SqlEnum
from app.database import Base
from sqlalchemy.orm import relationship


# Enum cho cột evaluation_type
class EvaluationType(str, Enum):
    """
    Định nghĩa các loại đánh giá có thể có.
    """
    initial = "initial"
    study = "study"
    discipline = "discipline"


class Evaluation(Base):
    """
    Model cho bảng evaluations.
    """
    __tablename__ = 'evaluations'

    evaluation_id = Column(Integer, primary_key=True)

    student_user_id = Column(Integer, ForeignKey('students.user_id', ondelete="CASCADE"), nullable=False)
    teacher_user_id = Column(Integer, ForeignKey('teachers.user_id', ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.class_id', ondelete="CASCADE"), nullable=False)
    evaluation_type = Column(SqlEnum(EvaluationType), nullable=False)
    evaluation_date = Column(Date, nullable=False)
    study_point = Column(Integer, nullable=False)
    discipline_point = Column(Integer, nullable=False)
    evaluation_content = Column(Text, nullable=False)

    # Mối quan hệ với học sinh và giáo viên và lớp (many-to-one)
    student = relationship("Student", back_populates="evaluations")
    teacher = relationship("Teacher", back_populates="evaluations")
    class_ = relationship("Class", back_populates="evaluations")
    def __repr__(self):
        return (
            f"<Evaluation(student_user_id={self.student_user_id}, "
            f"teacher_user_id={self.teacher_user_id}, type={self.evaluation_type}, "
            f"date={self.evaluation_date})>"
        )
