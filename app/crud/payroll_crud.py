from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Payroll
from app.schemas.payroll_schema import PayrollCreate, PayrollUpdate
from app.crud import notification_crud
from app.models.user_model import User
from app.models.teacher_model import Teacher
from app.models.tuition_model import PaymentStatus

def create_payroll_record(db: Session, payroll_in: PayrollCreate):
    db_payroll = Payroll(
        teacher_user_id=payroll_in.teacher_user_id,
        month=payroll_in.month,
        total_base_salary=payroll_in.total_base_salary,
        reward_bonus=payroll_in.reward_bonus,
        sent_at=payroll_in.sent_at,
        status=PaymentStatus.pending,
    )
    db.add(db_payroll)
    db.commit()
    db.refresh(db_payroll)  # total được DB tính sẵn
    return db_payroll

def get_all_payrolls(db: Session, skip: int = 0, limit: int = 100):
    results = (
        db.query(Payroll, User.full_name)
        .join(Teacher, Payroll.teacher_user_id == Teacher.user_id)
        .join(User, Teacher.user_id == User.user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return results

def get_payroll(db: Session, payroll_id: int):
    """
    Lấy một bản ghi payroll và tên đầy đủ của giáo viên dựa trên payroll_id.
    """
    # Thực hiện truy vấn JOIN để lấy dữ liệu từ cả ba bảng
    result = db.query(Payroll, User.full_name).join(
        Teacher, Payroll.teacher_user_id == Teacher.user_id
    ).join(
        User, Teacher.user_id == User.user_id
    ).filter(
        Payroll.payroll_id == payroll_id
    ).first()

    return result

def get_payrolls_by_teacher(db: Session, teacher_user_id: int, skip: int = 0, limit: int = 100):
    results = (
        db.query(Payroll, User.full_name)
        .join(Teacher, Payroll.teacher_user_id == Teacher.user_id)
        .join(User, Teacher.user_id == User.user_id)
        .filter(Payroll.teacher_user_id == teacher_user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return results

def update_payroll(db: Session, payroll_id: int, payroll_update: PayrollUpdate):
    db_payroll = db.query(Payroll).filter(Payroll.payroll_id == payroll_id).first()
    
    if not db_payroll:
        # Xử lý trường hợp không tìm thấy, nên trả về None hoặc raise HTTPException
        return None 
    
    # ✅ BỔ SUNG LOGIC: KHÔNG CHO PHÉP SỬA NẾU ĐÃ THANH TOÁN
    if db_payroll.status == PaymentStatus.paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể cập nhật bảng lương ID {payroll_id} vì trạng thái đã là 'paid'."
        )

    update_data = payroll_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_payroll, key, value)

    db.add(db_payroll)
    db.commit()
    db.refresh(db_payroll) 
    
    return db_payroll

def delete_payroll(db: Session, payroll_id: int):
    db_payroll = db.query(Payroll).filter(Payroll.payroll_id == payroll_id).first()
    
    if db_payroll:
        # Tạo lại nội dung thông báo để tìm kiếm
        notification_content = (
            f"Lương tháng {db_payroll.month}/{db_payroll.sent_at.year} của bạn đã được tính. "
            f"Tổng lương: {db_payroll.total:.2f}. "
            f"Thời gian: {db_payroll.sent_at.isoformat()}"
        )
        
        # Tìm notification
        # Giả sử notification_crud có một hàm để tìm kiếm theo nội dung và người nhận
        db_notification = notification_crud.get_notification_by_content_and_receiver(
            db, 
            content=notification_content, 
            receiver_id=db_payroll.teacher_user_id
        )
        
        # Nếu tìm thấy, xóa notification
        if db_notification:
            db.delete(db_notification)
            
        # Xóa bản ghi payroll
        db.delete(db_payroll)
        db.commit()

    return db_payroll