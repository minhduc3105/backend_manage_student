# backend/app/database.py (replace contents)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from pathlib import Path

# Try to find the credentials.env relative to project root
project_root = Path(__file__).resolve().parents[1]  # backend/app/.. -> backend
env_path = project_root / "credentials.env"
# Fallback to default search if not found
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    load_dotenv()  # load from any default .env in env

DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB")

if not all([DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError("Database environment variables are not set. Check credentials.env or environment.")

# Use psycopg2 driver explicitly to avoid async driver in sync code

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"DATABASE_URL: {DATABASE_URL}")  # Debugging line, remove in production")



# Create sync engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()