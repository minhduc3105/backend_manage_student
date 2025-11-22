from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from app.models.test_model import TestTypeEnum

class TestBase(BaseModel):
    test_id: Optional[int] = Field(None, example=1)
    test_name: str = Field(..., example="Bài kiểm tra giữa kỳ")
    student_user_id: int = Field(..., example=1)
    class_id: int = Field(..., example=1)
    class_name: Optional[str] = None  # Không bắt buộc
    teacher_user_id: int = Field(..., example=5)
    score: float = Field(..., example=8.5)
    exam_date: date = Field(..., example="2024-05-20")
    test_type: TestTypeEnum = Field(..., example="midterm")
    student_name: Optional[str] = None

class TestCreate(BaseModel):
    test_name: str = Field(..., example="Bài kiểm tra giữa kỳ")
    student_user_id: int = Field(..., example=1)
    class_id: int = Field(..., example=1)
    score: float = Field(..., example=8.5)
    exam_date: date = Field(..., example="2024-05-20")
    test_type: TestTypeEnum = Field(..., example="midterm")

class TestUpdate(BaseModel):
    test_name: Optional[str] = None
    score: Optional[float] = None
    exam_date: Optional[date] = None
    test_type: Optional[TestTypeEnum] = None

class Test(TestBase):
    test_id: int

    class Config:
        from_attributes = True
