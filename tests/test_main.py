import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- QUAN TRỌNG: Import app và get_db để tránh lỗi undefined name ---
# Import 'get_db' và 'Base' từ file database.py
from app.database import get_db, Base
# Import 'app' từ file main.py
from main import app

# 1. Cấu hình SQLite In-Memory (DB ảo)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo bảng trong DB ảo
Base.metadata.create_all(bind=engine)

# 2. Hàm Override (Hàm thay thế kết nối DB)
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# 3. Áp dụng Override
# Key [get_db] ở đây chính là hàm được import từ dòng 'from database import get_db'
app.dependency_overrides[get_db] = override_get_db

# Khởi tạo Client
client = TestClient(app)

# 4. Test Case
def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    # Đảm bảo nội dung này khớp với main.py
    assert response.json() == {"message": "Welcome to the Student Management API! Visit /docs for API documentation.My name is La Minh Duc"}