from sqlalchemy import Column, Computed, Integer, ForeignKey, Float, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.tuition_model import PaymentStatus

class Payroll(Base):
    """
    Model cho bảng payroll.
    """
    __tablename__ = 'payroll'

    payroll_id = Column(Integer, primary_key=True)

    teacher_user_id = Column(Integer, ForeignKey('teachers.user_id', ondelete="CASCADE"), nullable=False)

    month = Column(Integer, nullable=False)
    total_base_salary = Column(Float, nullable=False, default=0.0)
    reward_bonus = Column(Float, nullable=False, default=0.0)
    total = Column(Float, Computed("total_base_salary + reward_bonus"), nullable=False)
    sent_at = Column(DateTime, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    
    # Mối quan hệ với giáo viên (many-to-one, vì một giáo viên có thể có nhiều bản lương theo tháng)
    teacher = relationship("Teacher", back_populates="payroll")

    def __repr__(self):
        return f"<Payroll(teacher_user_id={self.teacher_user_id}, month={self.month}, total={self.total})>"