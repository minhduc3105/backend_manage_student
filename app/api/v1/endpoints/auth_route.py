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
from app.models.token_model import RefreshToken
from app.schemas.auth_schema import LoginRequest

# ✅ Chỉ import UserMeResponse cho /me
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

# ---------------------- LOCAL SCHEMA ---------------------- #
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
    from app.models.user_model import User
    
    username = data.username
    password = data.password
    user = db.query(User).filter(User.username == username).first()
    
    logger.info(f"Attempting login for user: {username}") 
    
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

    access_token = create_access_token({"sub": str(user.user_id)})
    refresh_token_str = create_refresh_token(user.user_id, db)
    
    logger.info(f"Login successful, refresh token: {refresh_token_str}")

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
    return json_response


# ---------------------- GOOGLE SSO (ĐÃ SỬA: INSERT user_roles TRỰC TIẾP) ---------------------- #
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
    # ✅ Import Local các Models cần thiết
    from app.models.user_model import User
    from app.models.student_model import Student
    
    # ✅ Import bảng trung gian user_roles
    from app.models.association_tables import user_roles 
    
    try:
        # 1. Lấy Token & User Info
        token_data = sso_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        user_info = sso_service.get_user_info(access_token)
        
        # 2. Check/Create User
        user = db.query(User).filter(User.email == user_info.email).first()
        if not user:
            user = User(
                username=user_info.email.split("@")[0],
                email=user_info.email,
                full_name=user_info.full_name,
                password="", 
                gender="male", 
                phone_number="", 
                date_of_birth=datetime(2000, 1, 1).date()
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 🔥🔥 2.1 LOGIC MỚI: INSERT TRỰC TIẾP VÀO BẢNG user_roles 🔥🔥
        # Role ID 3 = Student (theo yêu cầu của bạn)
        STUDENT_ROLE_ID = 3
        
        # Kiểm tra xem user này đã có role_id = 3 trong bảng user_roles chưa
        # Query trực tiếp vào bảng trung gian
        existing_role = db.query(user_roles).filter(
            user_roles.c.user_id == user.user_id,
            user_roles.c.role_id == STUDENT_ROLE_ID
        ).first()

        if not existing_role:
            logger.info(f"User {user.username} chưa có role_id={STUDENT_ROLE_ID}. Đang insert vào user_roles...")
            
            # Sử dụng câu lệnh INSERT của SQLAlchemy Core
            stmt = user_roles.insert().values(
                user_id=user.user_id,
                role_id=STUDENT_ROLE_ID
            )
            db.execute(stmt)
            db.commit()
            logger.info(f"✅ Đã insert (user_id={user.user_id}, role_id={STUDENT_ROLE_ID}) vào bảng user_roles")
        
        # 🔥🔥 3. LOGIC CŨ: Tự động thêm vào bảng STUDENTS 🔥🔥
        student_record = db.query(Student).filter(Student.user_id == user.user_id).first()
        
        if not student_record:
            logger.info(f"User {user.user_id} chưa có trong bảng Student. Đang tạo mới...")
            new_student = Student(
                user_id=user.user_id,
                parent_id=None 
            )
            db.add(new_student)
            db.commit()
            db.refresh(new_student)
            logger.info(f"✅ Đã tạo Student record cho User ID {user.user_id}")

        # 4. Tạo JWT & Refresh Token
        jwt_token = create_access_token(
            data={"sub": str(user.user_id)},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token_str = create_refresh_token(user.user_id, db)

        # 5. Redirect
        frontend_url = f"{FRONTEND_URL}/login/callback?token={jwt_token}"
        response = RedirectResponse(url=frontend_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPRIRE_DAYS
        )

        return response

    except Exception as e:
        logger.error(f"❌ Google login error: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=google_login_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )


# ---------------------- LẤY USER TỪ TOKEN (/me) ---------------------- #
@router.get("/me", response_model=UserMeResponse)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    from app.models.user_model import User
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai định dạng token")

    token = auth_header.split(" ")[1]
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    roles_list = [role.name for role in getattr(user, "roles", [])]
    dob_formatted = user.date_of_birth.strftime("%d/%m/%Y") if user.date_of_birth else None

    return UserMeResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        gender=user.gender,
        roles=roles_list, 
        phone=user.phone_number, 
        dob=dob_formatted 
    )


# ---------------------- REFRESH TOKEN ---------------------- #
@router.post("/refresh")
def refresh_token(
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    from app.models.user_model import User

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


# ---------------------- LOGOUT ---------------------- #
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