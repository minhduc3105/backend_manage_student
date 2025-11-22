# app/database/base_model.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Lớp cơ sở khai báo cho các mô hình SQLAlchemy 2.0.
    Tất cả các mô hình khác sẽ kế thừa từ lớp này.
    """
    pass

