# app/api/auth/auth_routes.py
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext 
from pydantic import BaseModel
from starlette.requests import Request
from dotenv import load_dotenv

from app.api.deps import get_db
from app.models.user_model import User
from app.models.token_model import RefreshToken
from app.schemas.auth_schema import LoginRequest

# ✅ Chỉ import UserMeResponse cho /me (Login giữ nguyên logic cũ nên không cần import LoginResponse từ schema)
from app.schemas.user_schema import UserMeResponse 

from app.api.auth.auth import (
    create_access_token,
    verify_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_refresh_token,
    REFRESH_TOKEN_EXPRIRE_DAYS
)
from app.services import sso_service

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# ---------------------- LOCAL SCHEMA (GIỮ NGUYÊN NHƯ CŨ) ---------------------- #
# Bạn muốn giữ login cũ nên tôi để class này ở đây như code gốc
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    full_name: str
    email: str
    roles: List[str]
    phone: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None


# ---------------------- LOGIN TRUYỀN THỐNG (GIỮ NGUYÊN) ---------------------- #
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username
    password = data.password
    user = db.query(User).filter(User.username == username).first()
    
    logger.info(f"Attempting login for user: {username}") 
    
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

    access_token = create_access_token({"sub": str(user.user_id)})
    refresh_token_str = create_refresh_token(user.user_id, db)
    
    logger.info(f"Login successful, refresh token: {refresh_token_str}")

    # Logic cũ của bạn
    user_roles_list = getattr(user, "roles", [])
    roles = [role.name for role in user_roles_list]

    login_data = LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        roles=roles, 
        phone=user.phone_number,
        dob=user.date_of_birth.strftime("%d/%m/%Y") if user.date_of_birth else None,
        gender=user.gender
    )

    json_response = JSONResponse(content=login_data.model_dump())

    json_response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        samesite="none",
        secure=True,
        domain=None, 
        max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPRIRE_DAYS
    )

    logger.info("--- DEBUG: ĐÃ TẠO RESPONSE, SẮP GỬI VỀ ---")
    return json_response


# ---------------------- GOOGLE SSO (GIỮ NGUYÊN) ---------------------- #
@router.get("/google")
def login_with_google():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&scope=openid%20email%20profile"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    try:
        # 1, 2, 3: (Giữ nguyên logic lấy Google Token và User như cũ)
        token_data = sso_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        user_info = sso_service.get_user_info(access_token)
        
        user = db.query(User).filter(User.email == user_info.email).first()
        if not user:
            # ... (logic tạo user mới giữ nguyên) ...
            db.add(user)
            db.commit()
            db.refresh(user)

        # 4. Tạo JWT Access Token
        jwt_token = create_access_token(
            data={"sub": str(user.user_id)},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 🔥 5. TẠO REFRESH TOKEN (Thêm đoạn này)
        refresh_token_str = create_refresh_token(user.user_id, db)

        # 6. Chuẩn bị Redirect Response
        frontend_url = f"{FRONTEND_URL}/login/callback?token={jwt_token}"
        response = RedirectResponse(url=frontend_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

        # 🔥 7. GẮN COOKIE VÀO RESPONSE (Quan trọng)
        # Trình duyệt sẽ tự động lưu cookie này khi nhận được redirect
        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,          # Frontend JS không đọc được (Bảo mật)
            secure=True,            # Chỉ chạy trên HTTPS (hoặc localhost)
            samesite="none",        # Để cookie hoạt động cross-site nếu cần
            max_age=60 * 60 * 24 * 7 # 7 ngày
        )

        return response

    except Exception as e:
        print(f"❌ Google login error: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=google_login_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )


# ---------------------- LẤY USER TỪ TOKEN (ĐÃ SỬA) ---------------------- #
@router.get("/me", response_model=UserMeResponse) # ✅ Sử dụng Schema mới
def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 1. Lấy Token từ Header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai định dạng token")

    token = auth_header.split(" ")[1]
    
    # 2. Verify Token & Lấy User
    token_data = verify_token(token)
    
    # ✅ Fetch user từ DB (Dùng biến 'user' thường)
    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Mapping dữ liệu (QUAN TRỌNG: Dùng 'user' thường, không dùng 'User' hoa)
    roles_list = [role.name for role in getattr(user, "roles", [])]
    dob_formatted = user.date_of_birth.strftime("%d/%m/%Y") if user.date_of_birth else None

    # 4. Trả về đúng Schema UserMeResponse để khớp với Frontend
    return UserMeResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        gender=user.gender,
        
        # Mapping Key:
        roles=roles_list,         # key 'roles'
        phone=user.phone_number,  # DB 'phone_number' -> Schema 'phone'
        dob=dob_formatted         # DB 'date_of_birth' -> Schema 'dob'
    )


# ---------------------- REFRESH TOKEN (GIỮ NGUYÊN) ---------------------- #
@router.post("/refresh")
def refresh_token(
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")

    token_record = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.revoked == False,
        RefreshToken.expired_at > datetime.now(timezone.utc)
    ).first()

    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.user_id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


# ---------------------- LOGOUT (GIỮ NGUYÊN) ---------------------- #
@router.post("/logout")
def logout(
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if refresh_token:
        token_record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        if token_record:
            db.query(RefreshToken).filter(
                RefreshToken.user_id == token_record.user_id,
                RefreshToken.revoked == False
            ).update({"revoked": True})
            db.commit()

    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("refresh_token")
    return response