from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, select
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List

from app.models.tuition_model import Tuition, PaymentStatus
from app.models.enrollment_model import Enrollment
from app.models.student_model import Student
from app.models.parent_model import Parent
from app.models.user_model import User
from app.models.class_model import Class
from app.models.notification_model import Notification # Import Model trực tiếp để bulk insert
from app.schemas.tuition_schema import TuitionCreate
from app.schemas.notification_schema import NotificationCreate
from app.crud.notification_crud import create_notification

# --- Helper ---
def _get_utc_now():
    return datetime.now(timezone.utc)

def _send_tuition_notification(
    db: Session, parent_user_id: int, student_name: str, amount: Decimal, due_date: date
):
    """Gửi thông báo lẻ (dùng cho create_tuition_record)"""
    month_str = due_date.strftime("%m/%Y")
    content = (
        f"Học phí tháng {month_str} của học sinh {student_name} là "
        f"{amount:,.0f} VND. Hạn thanh toán {due_date.strftime('%d/%m/%Y')}."
    )
    notif_in = NotificationCreate(
        sender_id=None, # System notification
        receiver_id=parent_user_id,
        content=content,
        type="tuition",
        sent_at=_get_utc_now(),
        is_read=False,
    )
    create_notification(db, notif_in)

# --- Main Functions ---

def calculate_tuition_for_student(db: Session, student_user_id: int) -> Decimal:
    """
    Tính tổng học phí: Tối ưu hóa bằng SQL Aggregation (SUM).
    Thay vì loop query N lần, chỉ query 1 lần.
    """
    total = db.query(func.sum(Class.fee)) \
        .join(Enrollment, Enrollment.class_id == Class.class_id) \
        .filter(
            Enrollment.student_user_id == student_user_id,
            Enrollment.enrollment_status == "active"
        ).scalar()
    
    return total if total else Decimal(0)


def create_tuition_record(db: Session, tuition_in: TuitionCreate):
    """
    Tạo bản ghi học phí thủ công cho 1 học sinh.
    Tối ưu: Fetch Parent và User info trong 1 luồng logic để tránh query rác.
    """
    # 1. Query thông tin liên kết (Student -> Parent -> User)
    # Sử dụng Aliased để join User 2 lần (1 cho Student, 1 cho Parent)
    StudentUser = aliased(User)
    ParentUser = aliased(User)

    result = db.query(Student, Parent, ParentUser, StudentUser) \
        .join(Parent, Student.parent_id == Parent.user_id) \
        .join(ParentUser, Parent.user_id == ParentUser.user_id) \
        .join(StudentUser, Student.user_id == StudentUser.user_id) \
        .filter(Student.user_id == tuition_in.student_user_id) \
        .first()

    if not result:
        raise ValueError("Không tìm thấy thông tin Học sinh hoặc Phụ huynh liên kết.")
    
    student, parent, parent_user, student_user = result

    # 2. Tạo Tuition
    tuition_record = Tuition(
        student_user_id=tuition_in.student_user_id,
        amount=tuition_in.amount,
        term=tuition_in.term,
        due_date=tuition_in.due_date,
        status=PaymentStatus.pending,
        created_at=_get_utc_now(),
        updated_at=_get_utc_now(),
    )
    db.add(tuition_record)
    
    # 3. Gửi thông báo
    _send_tuition_notification(
        db, parent_user.user_id, student_user.full_name, tuition_in.amount, tuition_in.due_date
    )
    
    # Commit 1 lần cuối cùng
    db.commit()
    db.refresh(tuition_record)
    return tuition_record


def create_tuition_for_all_students(db: Session, term: int, due_date: date):
    """
    Tạo học phí hàng loạt (Batch Processing).
    Đây là phần quan trọng nhất cần tối ưu.
    """
    # Alias cho User để phân biệt User của Student và User của Parent
    StudentUser = aliased(User, name="student_user")
    ParentUser = aliased(User, name="parent_user")

    # --- QUERY LỚN: Lấy tất cả dữ liệu cần thiết trong 1 lần truy vấn ---
    # Chọn: ID học sinh, Tên học sinh, ID phụ huynh, Tổng tiền học phí
    stmt = (
        db.query(
            Student.user_id.label("student_id"),
            StudentUser.full_name.label("student_name"),
            ParentUser.user_id.label("parent_id"),
            func.sum(Class.fee).label("total_amount")
        )
        .join(Enrollment, Student.user_id == Enrollment.student_user_id)
        .join(Class, Enrollment.class_id == Class.class_id)
        .join(StudentUser, Student.user_id == StudentUser.user_id) # Join lấy tên HS
        .join(Parent, Student.parent_id == Parent.user_id)       # Join lấy Parent
        .join(ParentUser, Parent.user_id == ParentUser.user_id)    # Join lấy User Parent (để gửi noti)
        .filter(Enrollment.enrollment_status == "active")
        .group_by(Student.user_id, StudentUser.full_name, ParentUser.user_id)
        .having(func.sum(Class.fee) > 0) # Chỉ lấy những em có học phí > 0
    )
    
    results = stmt.all()
    
    if not results:
        return []

    # --- PREPARE BATCH DATA ---
    tuition_objects = []
    notification_objects = []
    
    month_str = due_date.strftime("%m/%Y")
    due_date_str = due_date.strftime('%d/%m/%Y')
    now = _get_utc_now()

    for row in results:
        # 1. Tạo Tuition Object
        tuition = Tuition(
            student_user_id=row.student_id,
            amount=row.total_amount,
            term=term,
            due_date=due_date,
            status=PaymentStatus.pending,
            created_at=now,
            updated_at=now,
        )
        tuition_objects.append(tuition)

        # 2. Tạo Notification Object (trực tiếp Model, không qua CRUD lẻ)
        # Format content
        content = (
            f"Học phí tháng {month_str} của học sinh {row.student_name} là "
            f"{row.total_amount:,.0f} VND. Hạn thanh toán {due_date_str}."
        )
        
        notif = Notification(
            receiver_id=row.parent_id,
            content=content,
            type="tuition",
            sent_at=now,
            is_read=False
        )
        notification_objects.append(notif)

    # --- BULK INSERT & COMMIT ---
    try:
        # Thêm tất cả vào session
        db.add_all(tuition_objects)
        db.add_all(notification_objects)
        
        db.commit()
        
        # Refresh để lấy ID (nếu cần trả về) - Lưu ý: với số lượng lớn thì việc refresh all có thể chậm
        # Nếu chỉ cần trả về số lượng bản ghi thì không cần refresh.
        # Ở đây ta refresh các bản ghi tuition để trả về đúng yêu cầu hàm cũ
        for t in tuition_objects:
            db.refresh(t)
            
        return tuition_objects

    except Exception as e:
        db.rollback()
        raise e