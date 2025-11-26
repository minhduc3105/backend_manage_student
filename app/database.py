from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Import đúng nguồn: Lấy get_db và Base từ database.py
from database import get_db, Base 
from main import app

# 2. Cấu hình SQLite In-Memory (DB ảo)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo bảng trong DB ảo dựa trên Base lấy từ database.py
Base.metadata.create_all(bind=engine)

# 3. Hàm Override (Hàm thay thế)
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# 4. Áp dụng Override
# QUAN TRỌNG: Key trong dictionary này phải là hàm get_db được import từ database.py
app.dependency_overrides[get_db] = override_get_db

# Khởi tạo Client
client = TestClient(app)

# 5. Test Case
def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    # Đảm bảo message khớp với code trong main.py của bạn
    assert response.json() == {"message": "Welcome to the Student Management API! Visit /docs for API documentation."}
