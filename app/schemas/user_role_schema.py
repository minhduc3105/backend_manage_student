from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime 
from .user_schema import UserCreate
from .teacher_schema import TeacherCreate
from .student_schema import StudentCreate, StudentUpdate as StudentUpdateSchema
from .parent_schema import ParentCreate, ParentUpdate as ParentUpdateSchema

# ----------------- Base schemas for User and Role -----------------

class UserBase(BaseModel):
    username: str
    fullname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[bool] = None
    address: Optional[str] = None

class RoleBase(BaseModel):
    role_name: str

class RoleCreate(RoleBase):
    pass

class UserRoleInDB(RoleBase):
    role_id: int
    model_config = ConfigDict(from_attributes=True)

# ----------------- User and Role relationship schemas -----------------

class UserRoleCreate(BaseModel):
    user_id: int
    role_name: str  # Nếu DB dùng role_id thì nên thay đổi ở đây
    assigned_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ----------------- Composite schemas -----------------

class StudentCreateWithUser(BaseModel):
    user_data: UserCreate
    student_data: StudentCreate

class StudentUpdateWithUser(BaseModel):
    student_data: StudentUpdateSchema

class ParentCreateWithUser(BaseModel):
    user_data: UserCreate
    parent_data: ParentCreate

class ParentUpdateWithUser(BaseModel):
    parent_data: ParentUpdateSchema

class ManagerCreateWithUser(BaseModel):
    user_data: UserCreate
    # Nếu Manager có thêm fields riêng thì thêm manager_data ở đây

class TeacherCreateWithUser(BaseModel):
    user_data: UserCreate
    teacher_data: TeacherCreate
