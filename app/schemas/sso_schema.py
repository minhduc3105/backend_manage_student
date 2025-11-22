from pydantic import BaseModel

class GoogleAuthCode(BaseModel):
    code: str  # Mã code Google gửi về frontend (nếu bạn dùng PKCE flow)

class GoogleUserInfo(BaseModel):
    email: str
    full_name: str
    picture: str