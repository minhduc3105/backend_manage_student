from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date
from app.models.user_model import GenderEnum

# -------------------------------
# Base schema dùng chung (Giữ nguyên cho DB mapping)
# -------------------------------
class UserBase(BaseModel):
    username: str = Field(..., example="john_doe")
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    full_name: Optional[str] = Field(None, example="John Doe")
    date_of_birth: Optional[date] = Field(None, example="1990-01-01")
    gender: Optional[GenderEnum] = Field(None, example="male")
    phone_number: Optional[str] = Field(None, example="0901234567")

    @staticmethod
    def format_date_of_birth(date_of_birth: Optional[date]):
        if date_of_birth:
            return date_of_birth.strftime("%d/%m/%Y")
        return None

# =================================================================
# ✅ PHẦN THÊM MỚI: AUTH & FRONTEND SPECIFIC (DTO)
# Dùng riêng cho Login và /me để khớp 100% với Frontend React
# =================================================================

class UserMeResponse(BaseModel):
    """
    Schema dành riêng cho API /me (Get Current User).
    Định nghĩa tên trường (Key) đúng theo ý Frontend muốn: 'phone', 'dob', 'roles'.
    """
    user_id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    
    # 👇 Các trường đã được chuẩn hóa cho Frontend
    roles: List[str] = []         # Frontend cần 'roles'
    phone: Optional[str] = None   # Frontend cần 'phone' (map từ phone_number)
    dob: Optional[str] = None     # Frontend cần 'dob' (string dd/mm/yyyy)

    class Config:
        from_attributes = True

class LoginResponse(UserMeResponse):
    """
    Schema dành riêng cho Login.
    Kế thừa UserMeResponse nên có đủ info user + token.
    """
    access_token: str
    token_type: str = "bearer"
    message: str = "Login successful"

# =================================================================
# END PHẦN THÊM MỚI
# =================================================================


# -------------------------------
# Schema cho CRUD User (GIỮ NGUYÊN)
# -------------------------------
class UserCreate(UserBase):
    password: str = Field(..., example="password")

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None


class UserOut(UserBase):
    user_id: int = Field(..., example=1)
    password_changed: bool

    class Config:
        from_attributes = True

class UserView(BaseModel):
    user_id: int
    username: str
    roles: List[str]
    full_name: Optional[str]
    email: Optional[EmailStr]
    phone_number: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            date: UserBase.format_date_of_birth
        }
    
class UserViewDetails(UserBase):
    user_id: int
    user_roles: List[str]
    password_changed: bool

    class Config:
        from_attributes = True
        json_encoders = {
            date: UserBase.format_date_of_birth
        }

# -------------------------------
# Schema cho import từ Google Sheet (GIỮ NGUYÊN)
# -------------------------------
class SheetUserCreate(UserBase):
    password: str
    password_changed: bool = Field(default=False)
    roles: List[str]

class SheetUserImportRequest(BaseModel):
    users: List[SheetUserCreate]