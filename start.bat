@echo off
REM Chuyển đến thư mục dự án backend
cd backend

REM Kích hoạt môi trường ảo
call venv\Scripts\activate

REM Chạy máy chủ uvicorn (chạy song song với frontend)
uvicorn main:app --reload