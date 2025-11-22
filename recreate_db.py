from app.database import Base, engine, SessionLocal
from app.models import (
    user_model, manager_model, payroll_model, teacher_model, parent_model, student_model,
    subject_model, tuition_model, class_model, enrollment_model,
    attendance_model, evaluation_model, schedule_model, notification_model, teacher_review_model, test_model, role_model
)
from sqlalchemy import text

def recreate_database():
    print("Đang xóa tất cả các bảng cơ sở dữ liệu (sử dụng CASCADE)...")

    # Lấy tất cả tên bảng được quản lý bởi Base.metadata
    # Sử dụng reversed(Base.metadata.sorted_tables) để có thứ tự có khả năng an toàn hơn,
    # nhưng CASCADE sẽ xử lý phần lớn các phụ thuộc.
    all_table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]

    with engine.connect() as connection:
        for table_name in all_table_names:
            try:
                print(f"Đang xóa bảng: {table_name}")
                # Thực thi lệnh DROP TABLE với CASCADE
                connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
                connection.commit() # Commit mỗi lần xóa để đảm bảo thay đổi được áp dụng
            except Exception as e:
                # Nếu có lỗi, in ra và tiếp tục.
                # Trong phát triển, chúng ta muốn xóa sạch nhất có thể.
                print(f"Lỗi khi xóa bảng {table_name}: {e}")
                connection.rollback() # Rollback giao dịch hiện tại nếu có lỗi

    print("Đang tạo lại tất cả các bảng cơ sở dữ liệu...")
    # Sau khi xóa sạch, tạo lại tất cả các bảng từ các model hiện tại
    Base.metadata.create_all(bind=engine)
    print("Cơ sở dữ liệu đã được tạo lại thành công!")

if __name__ == "__main__":
    recreate_database()

