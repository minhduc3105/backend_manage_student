from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import List, Optional
from datetime import date
# Pydantic model cho payload của JWT
class TokenData(BaseModel):
    user_id: Optional[int] = None

# Pydantic model cho người dùng đã xác thực
class AuthenticatedUser(BaseModel):
    user_id: int = Field(..., example=1, description="ID của người dùng")
    username: str = Field(..., example="john_doe", description="Tên đăng nhập")
    roles: List[str] = Field(..., example=["manager"], description="Danh sách vai trò của người dùng")
    is_active: bool = Field(True, example=True, description="Trạng thái hoạt động của người dùng")
    full_name: Optional[str] = Field(None, example="John Doe", description="Họ và tên đầy đủ")
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com", description="Email của người dùng")

    class Config:
        from_attributes = True

        
class LoginRequest(BaseModel):
    """
    Schema cho yêu cầu đăng nhập.
    """
    username: str = Field(..., example="johndoe")
    password: str = Field(..., example="secure_password")

class LoginSuccess(BaseModel):
    """
    Schema cho phản hồi khi đăng nhập thành công.
    """
    message: str = Field(..., example="Đăng nhập thành công")
    user_id: int = Field(..., example=1)
    username: str = Field(..., example="johndoe")

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    message: Optional[str] = "Đăng nhập thành công"
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    roles: list = []
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None

    @field_serializer("date_of_birth")
    def format_date_of_birth(self, date_of_birth: date, _info):
        return date_of_birth.strftime("%d/%m/%Y")

    class Config:
        from_attributes = True