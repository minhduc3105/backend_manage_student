import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Response, Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.auth.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
)
from app.models.user_model import User
from datetime import timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username
    password = data.password
    user = db.query(User).filter(User.username == username).first()
    logger.info(f"Attempting login for user: {username}")
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

    access_token = create_access_token({"sub": user.user_id})
    refresh_token = create_refresh_token(user.user_id, db)
    logger.info(f"Login successful, refresh token: {refresh_token}")


    response = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"}
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # dev localhost
        samesite="Lax",
        max_age=60*60*24*7,
        path="/"
    )
    return response

@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    user = verify_refresh_token(refresh_token, db)
    if not user:
        # Nếu token hết hạn hoặc bị revoke, xóa cookie luôn
        response.delete_cookie("refresh_token", path="/")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token = create_access_token({"sub": user.user_id})
    return {"access_token": access_token}


@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        revoke_refresh_token(refresh_token, db)

    response.delete_cookie("refresh_token")
    return {"msg": "Logged out"}
