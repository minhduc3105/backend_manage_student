from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app, get_db
from database import Base

# 1. Cấu hình SQLite In-Memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Sửa lỗi chính tả: 'enginre' -> 'engine'
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Tạo Session và Table
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# 2. Hàm Override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# 3. Áp dụng Override
app.dependency_overrides[get_db] = override_get_db

# Khởi tạo Client
client = TestClient(app)

# 4. Test Case
def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Student Management API! Visit /docs for API documentation."}
