from pydantic import BaseModel
from typing import List, Dict

class TeacherOverview(BaseModel):
    total_students: int
    avg_gpa: float
    avg_study_point: float
    avg_discipline_point: float

    class Config:
        orm_mode = True


class StudentReport(BaseModel):
    id: int
    name: str
    gpa: float
    study_point: float
    discipline_point: float
    attendance: float

    class Config:
        orm_mode = True

class ClassReport(BaseModel):
    class_id: int
    class_name: str
    total_students: int
    avg_gpa: float
    avg_study_point: float
    avg_discipline_point: float
    grade_distribution: dict[int, int]  # key 1–10, value số học sinh
    students: List[StudentReport]

    class Config:
        orm_mode = True


class SalaryByMonth(BaseModel):
    month: int  # ví dụ: "2025-01"
    total: float

class TeacherReport(BaseModel):
    teacher_id: int
    teacher_name: str
    review_distribution: Dict[int, int]  # ví dụ: {1: 3, 2: 1, 3: 5, 4: 10, 5: 7}
    salary_by_month: List[SalaryByMonth]