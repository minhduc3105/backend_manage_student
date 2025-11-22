import requests
import os
from fastapi import HTTPException
from app.schemas.sso_schema import GoogleUserInfo

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")  

def exchange_code_for_token(code: str):
    """Đổi code lấy access_token từ Google và log chi tiết lỗi nếu có."""
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(GOOGLE_TOKEN_URL, data=data)

    # Nếu không thành công, raise lỗi chi tiết
    if response.status_code != 200:
        try:
            error_info = response.json()  # Lấy chi tiết JSON lỗi từ Google
        except Exception:
            error_info = response.text  # Nếu không parse được JSON, dùng raw text
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xác thực với Google. Status: {response.status_code}, Response: {error_info}"
        )

    # Nếu thành công, trả về JSON chứa access_token, id_token, refresh_token...
    return response.json()

def get_user_info(access_token: str) -> GoogleUserInfo:
    """Lấy thông tin người dùng từ Google."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Không thể lấy thông tin người dùng từ Google")
    data = response.json()
    return GoogleUserInfo(
        email=data["email"],
        full_name=data.get("name", ""),
        picture=data.get("picture", "")
    )
