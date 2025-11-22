# backend/app/crud/student_class_crud.py
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import select, insert, delete
from sqlalchemy.orm import Session
from app.schemas.enrollment_schema import EnrollmentCreate, EnrollmentView
from app.models.enrollment_model import Enrollment, EnrollmentStatus
from app.models.user_model import User
from app.models.class_model import Class # Import Class model

def get_enrollment(db: Session, student_user_id: int, class_id: int) -> Optional[EnrollmentView]:
    """Lấy bản ghi enrollment dựa trên student_user_id và class_id và trả về dưới dạng EnrollmentView."""
    stmt = (
        select(
            User.full_name.label("student_name"),
            Class.class_name,
            Enrollment.enrollment_date,
            Enrollment.enrollment_status
        )
        .join(User, Enrollment.student_user_id == User.user_id)
        .join(Class, Enrollment.class_id == Class.class_id)
        .where(
            Enrollment.student_user_id == student_user_id,
            Enrollment.class_id == class_id
        )
    )
    result = db.execute(stmt).first()
    if result:
        return EnrollmentView(
            student_name=result.student_name,
            class_name=result.class_name,
            enrollment_date=result.enrollment_date,
            enrollment_status=result.enrollment_status
        )
    return None

def get_enrollments_by_student_user_id(
    db: Session, student_user_id: int, skip: int = 0, limit: int = 100
) -> List[EnrollmentView]:
    """Lấy danh sách enrollments theo student_user_id và trả về dưới dạng EnrollmentView."""
    stmt = (
        select(
            User.full_name.label("student_name"),
            Class.class_name,
            Class.class_id,
            Enrollment.enrollment_date,
            Enrollment.enrollment_status
        )
        .join(User, Enrollment.student_user_id == User.user_id)
        .join(Class, Enrollment.class_id == Class.class_id)
        .where(Enrollment.student_user_id == student_user_id)
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(stmt).all()
    
    return [
        EnrollmentView(
            class_id=row.class_id,
            student_name=row.student_name,
            class_name=row.class_name,
            enrollment_date=row.enrollment_date,
            enrollment_status=row.enrollment_status
        )
        for row in results
    ]

def get_active_enrollments_by_class_id(
    db: Session, 
    class_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[EnrollmentView]:
    """
    Lấy danh sách enrollments đang active theo class_id và trả về dưới dạng EnrollmentView.
    """
    stmt = (
        select(
            User.full_name.label("student_name"),
            Class.class_name,
            Enrollment.enrollment_date,
            Enrollment.enrollment_status
        )
        .join(User, Enrollment.student_user_id == User.user_id)
        .join(Class, Enrollment.class_id == Class.class_id)
        .where(
            Enrollment.class_id == class_id,
            Enrollment.enrollment_status == EnrollmentStatus.active
        )
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(stmt).all()
    
    return [
        EnrollmentView(
            student_name=row.student_name,
            class_name=row.class_name,
            enrollment_date=row.enrollment_date,
            enrollment_status=row.enrollment_status
        )
        for row in results
    ]

def get_all_enrollments(db: Session, skip: int = 0, limit: int = 100) -> List[EnrollmentView]:
    """Lấy danh sách tất cả các enrollments và trả về dưới dạng EnrollmentView."""
    stmt = (
        select(
            User.full_name.label("student_name"),
            Class.class_name,
            Class.class_id,
            Enrollment.enrollment_date,
            Enrollment.enrollment_status
        )
        .join(User, Enrollment.student_user_id == User.user_id)
        .join(Class, Enrollment.class_id == Class.class_id)
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(stmt).all()
    
    return [
        EnrollmentView(
            class_id=row.class_id,
            student_name=row.student_name,
            class_name=row.class_name,
            enrollment_date=row.enrollment_date,
            enrollment_status=row.enrollment_status
        )
        for row in results
    ]

# ... (các hàm create, set_inactive, update không thay đổi) ...

def create_enrollment(db: Session, enrollment_in: EnrollmentCreate) -> Enrollment:
    # Kiểm tra user có tồn tại và có role = "student"
    user = db.execute(
        select(User).where(User.user_id == enrollment_in.student_user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_names = [role.name for role in user.roles]

    if "student" not in role_names:
        raise HTTPException(status_code=400, detail="User is not a student")

    db_enrollment = Enrollment(
        student_user_id=enrollment_in.student_user_id,
        class_id=enrollment_in.class_id,
        enrollment_date=enrollment_in.enrollment_date,
        enrollment_status=EnrollmentStatus.active
    )
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    return db_enrollment


def set_enrollment_inactive(db: Session, student_user_id: int, class_id: int) -> Optional[Enrollment]:
    """Cập nhật trạng thái enrollment thành inactive."""
    db_enrollment = get_enrollment(db, student_user_id, class_id)
    if not db_enrollment:
        return None

    db_enrollment.enrollment_status = EnrollmentStatus.inactive.value
    db.commit()
    db.refresh(db_enrollment)

    return db_enrollment


def update_enrollment(
    db: Session, enrollment_id: int, enrollment_update: dict
) -> Optional[Enrollment]:
    """Cập nhật thông tin của một enrollment theo enrollment_id."""
    db_enrollment = db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first()
    if db_enrollment:
        for key, value in enrollment_update.items():
            setattr(db_enrollment, key, value)
        db.commit()
        db.refresh(db_enrollment)
    return db_enrollment

