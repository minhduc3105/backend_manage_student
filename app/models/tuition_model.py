import enum
from sqlalchemy import Column, Integer, Float, DateTime, Enum, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class PaymentStatus(str, enum.Enum):
    """
    Enum để đại diện cho trạng thái thanh toán.
    """
    pending = "pending"
    paid = "paid"
    overdue = "overdue"


class Tuition(Base):
    """
    Mô hình database cho bảng `tuitions`.
    """
    __tablename__ = "tuitions"

    tuition_id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=True)  # Có thể null nếu chưa thanh toán
    term = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)

    # Quan hệ với bảng student
    student = relationship("Student", back_populates="tuitions")

    def __repr__(self):
        return (
            f"<Tuition(student_user_id={self.student_user_id}, amount={self.amount}, "
            f"status={self.payment_status}, due_date={self.due_date})>"
        )
