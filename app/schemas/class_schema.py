from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import date

class ClassBase(BaseModel):
    class_name: str = Field(..., example="Class 1A")
    teacher_user_id: Optional[int] = Field(None, example=1)
    subject_id: Optional[int] = Field(None, example=1)
    capacity: Optional[int] = Field(None, example=30)
    fee: Optional[int] = Field(None, example=1000)

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    class_name: Optional[str] = Field(None, example="Class 1A")
    teacher_user_id: Optional[int] = Field(None, example=1)
    subject_id: Optional[int] = Field(None, example=1)
    capacity: Optional[int] = Field(None, example=30)
    fee: Optional[int] = Field(None, example=1000)

class Class(ClassBase):
    class_id: int = Field(..., example=1)

    class Config:
        from_attributes = True

class ClassView(BaseModel):
    teacher_user_id: Optional[int]
    class_id: int
    class_name: str 
    teacher_name: Optional[str] 
    subject_name: Optional[str] 
    class_size : Optional[int]
    capacity: Optional[int]
    fee: Optional[int] 

class Student(BaseModel) :
    student_user_id: int
    full_name: Optional[str]
    email: Optional[str]
    date_of_birth: Optional[date]
    phone_number: Optional[str]
    gender: Optional[str]

    @field_serializer("date_of_birth")
    def format_date_of_birth(self, date_of_birth: date, _info):
        return date_of_birth.strftime("%d/%m/%Y")


