from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Optional
from app.models.evaluation_model import EvaluationType

# Lớp cơ sở chứa các thuộc tính chung
class EvaluationBase(BaseModel):
    """
    Schema cơ sở cho mô hình Evaluation.
    """
    teacher_user_id: int
    student_user_id: int
    class_id: int
    study_point: int
    discipline_point: int
    evaluation_type: EvaluationType
    evaluation_content: Optional[str] = None
    evaluation_date: date = date.today()

# Lớp dùng để tạo một bản ghi đánh giá mới
class EvaluationCreate(BaseModel):
    student_user_id: int
    study_point: int
    class_id: int
    discipline_point: int
    evaluation_type: EvaluationType
    evaluation_content: Optional[str] = None
    evaluation_date: date = date.today()

class EvaluationUpdate(BaseModel):
    study_point: Optional[int] = None
    discipline_point: Optional[int] = None
    evaluation_type: Optional[EvaluationType] = None
    evaluation_content: Optional[str] = None
    evaluation_date: Optional[date] = None

# Lớp dùng để đọc/trả về dữ liệu từ cơ sở dữ liệu
class Evaluation(EvaluationBase):
    """
    Schema để đọc dữ liệu đánh giá từ cơ sở dữ liệu.
    Bao gồm trường evaluation_id.
    """
    evaluation_id: int
    model_config = ConfigDict(from_attributes=True)    

class EvaluationSummary(BaseModel):
    student_user_id: int
    class_name: str
    subject: str
    final_study_point: int = Field(..., description="Tổng điểm học tập, giới hạn ở 100.")
    final_discipline_point: int = Field(..., description="Tổng điểm kỷ luật, giới hạn ở 100.")
    study_plus_count: int = Field(..., description="Số lần điểm học tập được cộng.")
    study_minus_count: int = Field(..., description="Số lần điểm học tập bị trừ.")
    discipline_plus_count: int = Field(..., description="Số lần điểm kỷ luật được cộng.")
    discipline_minus_count: int = Field(..., description="Số lần điểm kỷ luật bị trừ.")

    class Config:
        from_attributes = True

class EvaluationView(BaseModel):
    id: int
    class_name: str
    student_user_id: int
    student: str
    teacher: str
    type: EvaluationType
    content: Optional[str] = None
    date: date
