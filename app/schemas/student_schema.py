# app/schemas/student_schema.py

from datetime import date
from pydantic import BaseModel, field_serializer
from typing import Optional

class StudentBase(BaseModel):
    user_id: int
    parent_id: Optional[int] = None   # ✅ để Optional, không bắt buộc khi tạo

    class Config:
        from_attributes = True

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    parent_id: Optional[int] = None   # ✅ chỉ cập nhật parent_id

    class Config:
        from_attributes = True

class Student(StudentBase):
    user_id: int

    class Config:
        from_attributes = True

class StudentView(BaseModel):
    student_user_id: int
    class_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None

    @field_serializer("date_of_birth")
    def format_date_of_birth(self, date_of_birth: date, _info):
        return date_of_birth.strftime("%d/%m/%Y")