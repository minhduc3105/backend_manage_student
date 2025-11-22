# app/api/auth/auth_routes.py
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext  # type: ignore
from pydantic import BaseModel
from dotenv import load_dotenv
from starlette.requests import Request
import os

from app.api.deps import get_db
from app.models.user_model import User
from app.models.token_model import RefreshToken
from app.schemas.auth_schema import LoginRequest
from app.api.auth.auth import (
    create_access_token,
    verify_token,  # ✅ dùng verify_token từ auth.py
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPRIRE_DAYS,
)
from app.schemas.user_schema import UserOut
from app.services import sso_service
from app.api.auth.auth import create_refresh_token


logging.basicConfig(
    level=logging.INFO,  # Chọn INFO để hiện các logger.info
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# ---------------------- RESPONSE SCHEMA ---------------------- #
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


# ---------------------- LOGIN TRUYỀN THỐNG ---------------------- #
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username
    password = data.password
    user = db.query(User).filter(User.username == username).first()
    
    # Dòng log cũ của bạn
    logger.info(f"Attempting login for user: {username}") 
    
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

    access_token = create_access_token({"sub": user.user_id})
    refresh_token_str = create_refresh_token(user.user_id, db)
    
    logger.info(f"Login successful, refresh token: {refresh_token_str}")

    
    user_roles_list = getattr(user, "roles", [])
    
    
    # Đây là dòng code bạn đã sửa (rất quan trọng)
    roles = [role.name for role in user_roles_list]
    

    login_data = LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        roles=roles,  # Dòng này bây giờ sẽ nhận list[str]
        phone=user.phone_number,
        dob=user.date_of_birth.isoformat() if user.date_of_birth else None,
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




# ---------------------- GOOGLE SSO ---------------------- #
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
        # 1️⃣ Đổi code lấy token từ Google
        token_data = sso_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Không lấy được access_token từ Google")

        # 2️⃣ Lấy thông tin user từ Google
        user_info = sso_service.get_user_info(access_token)
        if not user_info.email:
            raise HTTPException(status_code=400, detail="Không lấy được thông tin người dùng từ Google")

        # 3️⃣ Kiểm tra hoặc tạo user mới trong DB
        user = db.query(User).filter(User.email == user_info.email).first()
        if not user:
            user = User(
                username=user_info.email.split("@")[0],
                email=user_info.email,
                full_name=user_info.full_name,
                password="",  # Không dùng password cho SSO
                gender="male",  # Mặc định hoặc lấy từ user_info nếu có
                phone_number="",  # Mặc định hoặc lấy từ user_info nếu có
                date_of_birth="2000-01-01"  # Mặc định hoặc lấy từ user_info nếu có"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 4️⃣ Tạo JWT token
        access_token = create_access_token(
            data={"sub": str(user.user_id)},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        refresh_token_str = create_refresh_token(user.user_id, db)


        frontend_url  = f"{FRONTEND_URL}/login/sso-success?access_token={access_token}"
        response = RedirectResponse(url=frontend_url, status_code=status.HTTP_302_FOUND)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            samesite="none",
            secure=True,
            domain=None,
            max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPRIRE_DAYS
        )
        
        return response

    except Exception as e:
        print(f"❌ Google login error: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=google_login_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )


# ---------------------- LẤY USER TỪ TOKEN ---------------------- #
@router.get("/me", response_model=UserOut)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    ✅ Trả về thông tin người dùng từ JWT token (Authorization header)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai định dạng token")

    token = auth_header.split(" ")[1]
    token_data = verify_token(token)
    user = db.query(User).filter(User.user_id == token_data.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ---------------------- REFRESH TOKEN ---------------------- #
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

    # Tạo access token mới
    new_access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": new_access_token, "token_type": "bearer"}

# ---------------------- LOGOUT ---------------------- #
@router.post("/logout")
def logout(
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if refresh_token:
        token_record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        if token_record:
            # ✅ Revoke tất cả token của user
            db.query(RefreshToken).filter(
                RefreshToken.user_id == token_record.user_id,
                RefreshToken.revoked == False
            ).update({"revoked": True})
            db.commit()


    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("refresh_token")
    return response



