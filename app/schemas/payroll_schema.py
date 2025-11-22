from typing import Optional
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from app.models.payroll_model import PaymentStatus

class PayrollBase(BaseModel):
    teacher_user_id: int
    month: int
    total_base_salary: float = 0.0
    reward_bonus: float = 0.0
    sent_at: datetime
    status: PaymentStatus = Field("paid")

    class Config:
        from_attributes = True

class PayrollCreate(BaseModel):
    teacher_user_id: int
    month: int
    total_base_salary: float = 0.0
    reward_bonus: float = 0.0
    sent_at: datetime


class PayrollUpdate(BaseModel):
    month: Optional[int] = None
    total_base_salary: Optional[float] = None
    reward_bonus: Optional[float] = None
    sent_at: Optional[datetime] = None
    status: Optional[PaymentStatus] = None
    class Config:
        from_attributes = True


class Payroll(PayrollBase):
    payroll_id: int
    total: float   # chỉ xuất hiện ở response
    status: PaymentStatus 
    
    class Config:
        from_attributes = True

class PayrollView(BaseModel):
    id: int
    teacher: str
    month: int
    base_salary: float
    bonus: float
    total: float
    status: PaymentStatus
    sent_at: datetime

    @field_serializer("sent_at")
    def format_sent_at(self, sent_at: datetime,):
        return sent_at.strftime("%d/%m/%Y")