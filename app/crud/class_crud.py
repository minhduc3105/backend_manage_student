from sqlalchemy.orm import Session
from sqlalchemy import select, join
from typing import List

from app.models.class_model import Class
from app.models.user_model import User
from app.models.subject_model import Subject
from app.models.enrollment_model import Enrollment
from app.schemas.class_schema import ClassCreate, ClassUpdate, ClassView, Student
from app.models.enrollment_model import EnrollmentStatus

def get_class_with_teacher_name_query():
    return (
        select(
            Class.class_id,
            Class.teacher_user_id,
            Class.class_name,
            User.full_name.label("teacher_name"),
            Subject.name.label("subject_name"),
            Class.capacity,
            Class.class_size,  
            Class.fee
        )
        .join(Subject, Class.subject_id == Subject.subject_id)
        .outerjoin(User, Class.teacher_user_id == User.user_id)
    )

def get_class(db: Session, class_id: int):
    query = get_class_with_teacher_name_query().where(Class.class_id == class_id)
    result = db.execute(query).first()
    if result:
        return ClassView.model_validate(result._asdict())
    return None

def get_class_by_name(db: Session, class_name: str):
    query = get_class_with_teacher_name_query().where(Class.class_name == class_name)
    result = db.execute(query).first()
    if result:
        return ClassView.model_validate(result._asdict())
    return None

def get_classes_by_teacher_user_id(db: Session, teacher_user_id: int, skip: int = 0, limit: int = 100) -> List[ClassView]:
    query = (
        get_class_with_teacher_name_query()
        .where(Class.teacher_user_id == teacher_user_id)
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(query).all()
    return [ClassView.model_validate(row._asdict()) for row in results]

def get_active_classes_by_student_user_id(db: Session, student_user_id: int, skip: int = 0, limit: int = 100) -> List[ClassView]:
    query = (
        get_class_with_teacher_name_query()
        .join(Enrollment, Class.class_id == Enrollment.class_id)
        .where(
            (Enrollment.student_user_id == student_user_id) &
            (Enrollment.enrollment_status == EnrollmentStatus.active)
        )
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(query).all()
    return [ClassView.model_validate(row._asdict()) for row in results]

def get_all_classes(db: Session, skip: int = 0, limit: int = 100) -> List[ClassView]:
    query = get_class_with_teacher_name_query().offset(skip).limit(limit)
    results = db.execute(query).all()
    return [ClassView.model_validate(row._asdict()) for row in results]

def create_class(db: Session, class_data: ClassCreate):
    db_class = Class(**class_data.model_dump())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

def update_class(db: Session, class_id: int, class_update: ClassUpdate):
    db_class = db.query(Class).filter(Class.class_id == class_id).first()
    if db_class:
        update_data = class_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_class, key, value)
        db.add(db_class)
        db.commit()
        db.refresh(db_class)
    return db_class

def delete_class(db: Session, class_id: int):
    db_class = db.query(Class).filter(Class.class_id == class_id).first()
    if not db_class:
        return None
    deleted_data = db_class
    db.delete(db_class)
    db.commit()
    return deleted_data

def get_students_list(db: Session, class_id: int, skip: int = 0, limit: int = 100) -> List[Student]:
    """
    Trả về danh sách học sinh của lớp `class_id` theo schema Student,
    chỉ lấy những enrollment có trạng thái active.
    """
    query = (
        select(
            User.user_id.label("student_user_id"),
            User.full_name,
            User.email,
            User.date_of_birth,
            User.phone_number,
            User.gender,
        )
        .select_from(
            join(
                Enrollment,
                User,
                Enrollment.student_user_id == User.user_id,
            )
        )
        .where(
            (Enrollment.class_id == class_id) &
            (Enrollment.enrollment_status == EnrollmentStatus.active)
        )
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )



    results = db.execute(query).all()
    return [Student.model_validate(row._asdict()) for row in results]

