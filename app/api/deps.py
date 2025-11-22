# app/api/deps.py
from typing import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """Dependency để lấy phiên cơ sở dữ liệu."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# def get_current_user(
#     db: Session = Depends(get_db),
#     token: str = Depends(reusable_oauth2)
# ) -> User:
#     """
#     Xác thực JWT token và trả về đối tượng User.
#     """
    
#     # 1. Xác thực Token
#     # verify_token sẽ kiểm tra tính hợp lệ, hết hạn, và lấy ra payload (sub/user_id)
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Token không hợp lệ hoặc đã hết hạn",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
    
#     # Payload chứa user_id (sub)
#     payload = verify_token(token, credentials_exception)
#     user_id = payload.get("sub")
    
#     if user_id is None:
#         raise credentials_exception

#     # 2. Tải User từ DB
#     user = db.query(User).filter(User.user_id == int(user_id)).first()

#     if user is None:
#         raise credentials_exception # Token hợp lệ nhưng user không tồn tại

#     return user


