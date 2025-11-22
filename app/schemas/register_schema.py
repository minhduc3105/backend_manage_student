#register_schema
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# Thêm các trường dữ liệu mới cho người dùng
class UserInfo(BaseModel):
    email: Optional[str] = Field(None, example="john.doe@example.com")
    password: str = Field(..., example="verysecretpassword")
    role: str = Field(..., example="teacher")
    
    # Các trường bổ sung đã được thêm vào
    full_name: Optional[str] = Field(None, example="John Doe")
    date_of_birth: Optional[date] = Field(None, example="1990-01-01")
    gender: Optional[str] = Field(None, example="Male")
    phone_number: Optional[str] = Field(None, example="0901234567")

class RegisterRequest(BaseModel):
    user_info: UserInfo
    role: Optional[dict] = Field(None)

# -----------------
# Schema cho Endpoint "parent-and-children"
# -----------------
class StudentInfoInRequest(BaseModel):
    full_name: str = Field(..., example="Jane Doe")
    email: str = Field(..., example="jane.doe@example.com") 
    date_of_birth: date = Field(..., example="2010-05-15")
    gender: Optional[str] = Field(None, example="Female")
    class_id: Optional[int] = Field(None, example=1)
    phone_number: Optional[str] = Field(None, example="0909876543")

class ParentAndChildrenRequest(BaseModel):
    username: str = Field(..., example="parent_jane")
    email: str = Field(None, example="parent.jane@example.com")
    password: str = Field(..., example="secure_password")
    full_name: Optional[str] = Field(None, example="Jane Parent")
    date_of_birth: Optional[date] = Field(None, example="1985-03-20")
    gender: Optional[str] = Field(None, example="Female")
    phone_number: Optional[str] = Field(None, example="0912345678")
    children_info: List[StudentInfoInRequest] = Field(...)

# -----------------
# Schema cho Endpoint "student-with-existing-parent"
# -----------------
class RegisterStudentWithParentRequest(BaseModel):
    parent_user_id: int = Field(..., example=1)
    student_info: StudentInfoInRequest
