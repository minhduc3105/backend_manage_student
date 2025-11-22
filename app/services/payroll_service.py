from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Import Models
from app.models.teacher_model import Teacher
from app.models.payroll_model import PaymentStatus, Payroll as PayrollModel # Cần import Model để bulk insert
from app.models.notification_model import Notification as NotificationModel, NotificationType # Cần import Model

# Import Schemas
from app.schemas.payroll_schema import PayrollCreate, PayrollUpdate, Payroll
from app.schemas.notification_schema import NotificationCreate

# Import CRUD
from app.crud import payroll_crud, notification_crud, teacher_crud

# --- Helper Functions ---

def _get_current_utc_time() -> datetime:
    """Hàm helper để lấy giờ chuẩn, đảm bảo nhất quán"""
    return datetime.now(timezone.utc)

def _create_notification_content(month: int, year: int, total: float, sent_at: datetime) -> str:
    """Format nội dung thông báo để tái sử dụng"""
    return (
        f"Lương tháng {month}/{year} của bạn đã được tính. "
        f"Tổng lương: {total:,.2f}. " # Thêm dấu phẩy ngăn cách hàng nghìn cho dễ đọc
        f"Thời gian: {sent_at.strftime('%d/%m/%Y %H:%M')}" # Format ngày giờ dễ đọc hơn isoformat
    )

# --- Main Services ---

def create_payroll(db: Session, teacher: Teacher, payroll_in: PayrollCreate) -> Payroll:
    """
    Tạo một bản ghi lương lẻ (Single Transaction).
    """
    # 1. Tạo Payroll
    db_payroll = payroll_crud.create_payroll_record(db, payroll_in)

    # 2. Tạo Notification
    content = _create_notification_content(
        db_payroll.month, 
        db_payroll.sent_at.year, 
        db_payroll.total, 
        db_payroll.sent_at
    )

    notification_in = NotificationCreate(
        receiver_id=teacher.user_id,
        content=content,
        type="payroll", # Nên dùng Enum nếu có (NotificationType.payroll)
        sent_at=db_payroll.sent_at,
        is_read=False
    )
    notification_crud.create_notification(db, notification_in)

    return Payroll.from_orm(db_payroll)


def run_monthly_payroll(db: Session) -> List[Payroll]:
    """
    Chạy tính lương hàng loạt (Batch Processing - Optimized Transaction).
    Sử dụng 1 Transaction duy nhất cho toàn bộ giáo viên.
    """
    now = _get_current_utc_time()
    month = now.month
    year = now.year

    teachers = teacher_crud.get_all_teachers(db)
    
    payroll_objects = []
    notification_objects = []
    
    # Danh sách kết quả để trả về
    results = []

    # 1. Tính toán dữ liệu trong bộ nhớ (In-memory preparation)
    for teacher in teachers:
        # Lưu ý: Nếu teacher_crud.get_classes... thực hiện query DB, 
        # đoạn này vẫn bị N+1 Query. Để tối ưu triệt để, cần viết lại query 
        # lấy tổng số lớp của TẤT CẢ giáo viên trong 1 lần gọi (SQL Group By).
        classes = teacher_crud.get_classes_taught_by_teacher(
            db, teacher.user_id, month=month, year=year
        )
        total_classes = len(classes)
        
        # Sử dụng getattr hoặc 0.0 để an toàn hơn
        base_salary_per_class = teacher_crud.get_teacher_base_salary(db, teacher.user_id) or 0.0
        reward_bonus = teacher_crud.get_teacher_reward_bonus(db, teacher.user_id) or 0.0
        
        total_salary = (total_classes * base_salary_per_class) + reward_bonus

        # Tạo ORM Object cho Payroll (chưa commit)
        payroll_orm = PayrollModel(
            teacher_user_id=teacher.user_id,
            month=month,
            total_base_salary=total_classes * base_salary_per_class,
            reward_bonus=reward_bonus,
            total=total_salary, # Giả định Model có cột total, nếu là computed property thì bỏ dòng này
            sent_at=now,
            status=PaymentStatus.pending
        )
        payroll_objects.append(payroll_orm)

    # 2. Bulk Insert Payrolls (Flush để lấy ID và default values nhưng chưa commit)
    db.add_all(payroll_objects)
    db.flush() 

    # 3. Tạo Notifications dựa trên Payrolls đã flush (đã có ID/Data)
    for payroll in payroll_objects:
        content = _create_notification_content(
            payroll.month, 
            year, # Dùng biến year local vì sent_at trong DB có thể lệch milisecond
            payroll.total, 
            payroll.sent_at
        )
        
        notif_orm = NotificationModel(
            receiver_id=payroll.teacher_user_id,
            content=content,
            type="payroll",
            sent_at=now,
            is_read=False
        )
        notification_objects.append(notif_orm)
        
        # Convert sang Pydantic để trả về kết quả
        results.append(Payroll.from_orm(payroll))

    # 4. Bulk Insert Notifications
    db.add_all(notification_objects)

    # 5. Commit transaction duy nhất
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi tính lương hàng loạt: {str(e)}")

    return results


def update_payroll_with_notification(db: Session, payroll_id: int, payroll_update: PayrollUpdate) -> Payroll:
    """
    Cập nhật lương và gửi thông báo mới.
    """
    # Update Payroll
    db_payroll = payroll_crud.update_payroll(db, payroll_id, payroll_update)
    if not db_payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")

    # Create Notification
    content = _create_notification_content(
        db_payroll.month, 
        db_payroll.sent_at.year, 
        db_payroll.total, 
        db_payroll.sent_at
    )

    notification_in = NotificationCreate(
        receiver_id=db_payroll.teacher_user_id,
        content=content,
        type="payroll",
        sent_at=_get_current_utc_time(),
        is_read=False
    )
    notification_crud.create_notification(db, notification_in)

    return Payroll.from_orm(db_payroll)