from sqlalchemy import Column, Integer, String, Date, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.association_tables import user_roles
from app.models.token_model import RefreshToken
from enum import Enum as PyEnum
from passlib.context import CryptContext   # ✅ thêm dòng này

# ✅ Khởi tạo context cho hashing/verify password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class GenderEnum(PyEnum):
    male = "male"
    female = "female"
    other = "other"


class User(Base):
    """
    Model for the users table.
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    gender = Column(Enum(GenderEnum, name='gender_enum'), nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)

    password_changed = Column(Boolean, default=False, nullable=False)

    roles = relationship("Role", secondary=user_roles, back_populates="users", passive_deletes=True)
    manager = relationship("Manager", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    teacher = relationship("Teacher", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    student = relationship("Student", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    parent = relationship("Parent", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", single_parent=True)

    def __repr__(self):
        return (
            f"<User(user_id={self.user_id}, username='{self.username}', "
            f"password_changed={self.password_changed})>"
        )

    # ✅ Kiểm tra mật khẩu
    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password.encode('utf-8')[:72], self.password)

    # ✅ (tuỳ chọn) Hàm để đặt mật khẩu mới
    def set_password(self, plain_password: str):
        self.password = pwd_context.hash(plain_password.encode('utf-8')[:72])
