# Student Management Backend API

Backend API cho hệ thống **Quản lý Sinh viên**, được xây dựng bằng **FastAPI** và **SQLAlchemy**.  
Hệ thống cung cấp các API phục vụ quản lý sinh viên, lớp học, học phí và tác vụ tự động.

##  Công nghệ sử dụng

- Python 3.8+
- FastAPI
- SQLAlchemy
- APScheduler
- Uvicorn
- CORS Middleware
- Session Middleware

## Tính năng chính

### Quản lý sinh viên
- Thêm sinh viên
- Cập nhật thông tin
- Xóa sinh viên
- Lấy danh sách sinh viên

### Quản lý lớp học
- Tạo lớp
- Phân công sinh viên
- Xem danh sách lớp

### Quản lý học phí
- Theo dõi học phí
- Cập nhật trạng thái thanh toán
- Tự động cập nhật học phí quá hạn

## Tác vụ tự động

Hệ thống sử dụng APScheduler để:

- Chạy tác vụ cập nhật học phí quá hạn mỗi ngày lúc 00:00
- Tự động xử lý nghiệp vụ mà không cần gọi API thủ công

---

## 🛠️ Cài đặt và chạy dự án

### Clone repository

```bash
git clone https://github.com/minhduc3105/backend_manage_student.git
cd backend_manage_student
```
### Tạo môi trường ảo
```bash
python -m venv venv
```
### Kích hoạt
```bash
venv\Scripts\activate (Window)
source venv/bin/activate (Mac, Linux)
```
### Cài đặt dependencies
```bash
pip install -r requirements.txt
```
###Chạy server
```bash
uvicorn main:app --reload
```
## Database
- Sử dụng SQLAlchemy ORM
- Tự động tạo bảng khi khởi động
- Có thể cấu hình SQLite / MySQL / PostgreSQL


## Tác giả
Minh Đức
- GitHub: https://github.com/minhduc3105


Duy Anh
- Github: https://github.com/danny2708

Phúc Anh
- Github: https://github.com/chimsedinanghehe



