from datetime import date, datetime
from pydantic import BaseModel, field_serializer
from typing import Optional, List

class TeacherBase(BaseModel):
    """
    Schema cơ sở cho Giáo viên, chứa các trường dùng chung.
    """
    user_id: int
    base_salary_per_class:  Optional[float]
    reward_bonus:  Optional[float]

    class Config:
        from_attributes = True

class TeacherCreate(TeacherBase):
    """
    Schema cho việc tạo một Giáo viên mới.
    """
    pass

class TeacherUpdate(BaseModel):
    """
    Schema cho việc cập nhật thông tin Giáo viên.
    Các trường là tùy chọn (Optional).
    """
    base_salary_per_class: Optional[float] = None
    reward_bonus: Optional[float] = None

class Teacher(TeacherBase):
    """
    Schema cho mô hình Giáo viên đã hoàn chỉnh, bao gồm teacher_id.
    """
    user_id: int

    class Config:
        from_attributes = True

class TeacherAssign(BaseModel):
    """
    Schema chỉ dùng để gán vai trò Giáo viên, chỉ cần teacher_user_id.
    """
    user_id: int

class ClassTaught(BaseModel):
    class_id: int
    teacher_user_id: int
    class_name: str 
    teacher_name: Optional[str] 
    subject_name: Optional[str] 
    capacity: Optional[int]
    fee: Optional[int] 

class TeacherStats(BaseModel):
    class_taught: int
    schedules: int
    reviews: int
    rate: float

class TeacherView(BaseModel):
    teacher_user_id: int
    full_name: str
    email: str
    date_of_birth: date
    class_taught: Optional[List[str]]

    @field_serializer("date_of_birth")
    def format_date_of_birth(self, date_of_birth: date, _info):
        return date_of_birth.strftime("%d/%m/%Y") if date_of_birth else None