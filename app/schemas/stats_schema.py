from pydantic import BaseModel, Field
from typing import Optional

class Stats(BaseModel):
    total_classes: int
    total_teachers: int
    total_students: int
    total_schedules: int

    class Config:
        from_attributes = True

class SubjectStats(BaseModel):
    subject_id: int
    subject_name: str
    total_classes: int

    class Config:
        from_attributes = True

class StudentStats(BaseModel):
    classes_enrolled: Optional[int] = Field(..., description="Số lớp đã đăng ký")
    gpa: Optional[float] = Field(None, description="Điểm trung bình học tập")
    study_point: Optional[int] = Field(None, description="Điểm học tập")
    discipline_point: Optional[int] = Field(None, description="Điểm kỷ luật")