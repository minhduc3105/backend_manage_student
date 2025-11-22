from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext # type: ignore

from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserUpdate
from app.schemas.user_schema import UserView, UserViewDetails

# bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def is_bcrypt_hash(password: str) -> bool:
    # Bcrypt hash thường bắt đầu bằng $2b$, $2a$, hoặc $2y$
    return isinstance(password, str) and (
        password.startswith("$2b$") or password.startswith("$2a$") or password.startswith("$2y$")
    )

def get_user(db: Session, user_id: int) -> Optional[UserViewDetails]:
    """
    Truy vấn người dùng bằng ID và trả về thông tin chi tiết.
    """
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        return None
    
    # Chuyển đổi danh sách đối tượng Role thành danh sách chuỗi tên vai trò
    user_roles_list = [role.name for role in db_user.roles]
    
    # Tạo đối tượng UserViewDetails từ db_user
    return UserViewDetails(
        user_id=db_user.user_id,
        username=db_user.username,
        user_roles=user_roles_list,
        full_name=db_user.full_name,
        email=db_user.email,
        phone_number=db_user.phone_number,
        password_changed=db_user.password_changed,
        date_of_birth=db_user.date_of_birth,
        gender=db_user.gender,
    )

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserView]:
    """
    Truy vấn danh sách tất cả người dùng và trả về thông tin cơ bản.
    """
    db_users = db.query(User).offset(skip).limit(limit).all()
    
    users_view = []
    for user in db_users:
        # Chuyển đổi danh sách đối tượng Role thành danh sách chuỗi tên vai trò
        user_roles_list = [role.name for role in user.roles]
        
        users_view.append(
            UserView(
                user_id=user.user_id,
                username=user.username,
                roles=user_roles_list,
                full_name=user.full_name,
                email=user.email,
                phone_number=user.phone_number
            )
        )
    return users_view

def create_user(db: Session, user: UserCreate) -> User:
    """
    Tạo một người dùng mới trong cơ sở dữ liệu.
    Lưu first_password (raw), password = hash(first_password).
    """

    # Chỉ hash nếu chưa phải là hash bcrypt
    password = user.password
    if not is_bcrypt_hash(password):
        password = pwd_context.hash(password.encode('utf-8')[:72])
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        phone_number=user.phone_number,
        password_changed=False,                
        password=password,    
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """
    Cập nhật thông tin của một người dùng đã tồn tại.
    Nếu có password mới → hash lại và set password_changed = True.
    """
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)

    # Nếu có password mới → hash và set password_changed = True
    if "password" in update_data and update_data["password"]:
        if not is_bcrypt_hash(update_data["password"]):
            update_data["password"] = pwd_context.hash(update_data["password"])
        db_user.password_changed = True  # gán trực tiếp vào entity

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> Optional[User]:
    """
    Xóa một người dùng cụ thể khỏi cơ sở dữ liệu.
    """
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        return None

    # Xóa quan hệ many-to-many trước (nếu có roles gắn với user)
    db_user.roles.clear()
    db.commit()  # flush thay đổi vào bảng trung gian

    # Xóa user
    db.delete(db_user)
    db.commit()
    return db_user