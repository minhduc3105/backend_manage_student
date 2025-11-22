# app/schemas/enrollment_schema.py
from pydantic import BaseModel, Field, field_serializer
from datetime import date
from typing import Optional
from app.models.enrollment_model import EnrollmentStatus

class EnrollmentBase(BaseModel):
    student_user_id: int = Field(..., example=1)
    class_id: int = Field(..., example=1)
    enrollment_date: date = Field(..., example="2023-10-26")
    enrollment_status: EnrollmentStatus = Field(..., example="active", description="Trạng thái: active, inactive")

class EnrollmentCreate(BaseModel):
    student_user_id: int = Field(..., example=1)
    class_id: int = Field(..., example=1)
    enrollment_date: date = Field(..., example="2023-10-26")

class EnrollmentUpdate(BaseModel):
    """Schema để cập nhật một bản ghi enrollment."""
    student_user_id: Optional[int] = None
    class_id: Optional[int] = None
    enrollment_date: Optional[date] = None
    enrollment_status: Optional[EnrollmentStatus] = None

class Enrollment(EnrollmentBase):
    enrollment_id: int = Field(..., example=1001)

    class Config:
        from_attributes = True

class EnrollmentView(BaseModel):
    class_id: int
    student_name: str 
    class_name: str 
    enrollment_date: date = Field(..., example="2023-10-26")
    enrollment_status: EnrollmentStatus = Field(..., example="active", description="Trạng thái: active, inactive")

    @field_serializer("enrollment_date")
    def format_enrollment_date(self, enrollment_date: date):
        return enrollment_date.strftime("%d/%m/%Y")