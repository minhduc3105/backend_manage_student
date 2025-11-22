# Trong file app/crud/tuition_crud.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from app.models.tuition_model import Tuition, PaymentStatus
from app.schemas.tuition_schema import TuitionCreate, TuitionUpdate
from app.models.user_model import User
from app.models.student_model import Student


def get_tuition(db: Session, tuition_id: int) -> Optional[Tuple[Tuition, str]]:
    """Lấy một bản ghi học phí và tên đầy đủ của học sinh."""
    return db.query(Tuition, User.full_name).join(
        User, Tuition.student_user_id == User.user_id
    ).filter(
        Tuition.tuition_id == tuition_id
    ).first()

def get_all_tuitions_with_student_name(db: Session, skip: int = 0, limit: int = 100) -> List[Tuple[Tuition, str]]:
    """Lấy danh sách tất cả học phí, bao gồm tên đầy đủ của học sinh."""
    return db.query(Tuition, User.full_name).join(
        User, Tuition.student_user_id == User.user_id
    ).offset(skip).limit(limit).all()

def get_tuitions_by_student_user_id(db: Session, student_user_id: int, skip: int = 0, limit: int = 100) -> List[Tuple[Tuition, str]]:
    """Lấy danh sách học phí của một học sinh, bao gồm tên đầy đủ."""
    return db.query(Tuition, User.full_name).join(
        User, Tuition.student_user_id == User.user_id
    ).filter(
        Tuition.student_user_id == student_user_id
    ).offset(skip).limit(limit).all()


def get_tuitions_by_parent_user_id(db: Session, parent_user_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(Tuition, User.full_name)
        .join(User, Tuition.student_user_id == User.user_id)
        .join(Student, Student.user_id == Tuition.student_user_id)
        .filter(Student.parent_id == parent_user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )



def create_tuition(db: Session, tuition: TuitionCreate):
    """
    Tạo học phí (thuần DB, không gửi thông báo).
    Service sẽ gọi hàm này và chịu trách nhiệm gửi notification.
    """
    db_tuition = Tuition(
        **tuition.model_dump(),
        status=PaymentStatus.pending
    )
    db.add(db_tuition)
    db.commit()
    db.refresh(db_tuition)
    return db_tuition


def update_tuition(db: Session, tuition_id: int, tuition_update: TuitionUpdate):
    """Cập nhật các chi tiết về học phí như amount, term, due_date."""
    # Sửa: Lấy tuple và kiểm tra. db_tuition là phần tử đầu tiên của tuple.
    result = get_tuition(db, tuition_id)
    if not result:
        return None
        
    db_tuition, _ = result  # Giải nén tuple, bỏ qua fullname

    # Không cho phép cập nhật nếu đã thanh toán
    if db_tuition.status == PaymentStatus.paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể cập nhật học phí ID {tuition_id} vì trạng thái đã là 'paid'."
        )

    update_data = tuition_update.model_dump(exclude_unset=True)
    update_data.pop("student_user_id", None)

    for key, value in update_data.items():
        setattr(db_tuition, key, value)

    db.commit()
    db.refresh(db_tuition)
    return db_tuition


def delete_tuition(db: Session, tuition_id: int):
    db_tuition = db.query(Tuition).filter(Tuition.tuition_id == tuition_id).first()
    if not db_tuition:
        return None
    db.delete(db_tuition)
    db.commit()
    return True