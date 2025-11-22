# app/crud/teacher_review_crud.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.teacher_review_model import TeacherReview
from app.schemas.teacher_review_schema import TeacherReviewCreate, TeacherReviewUpdate, TeacherReviewView
from datetime import datetime
import logging
from typing import List
from app.models.user_model import User
from sqlalchemy import select, join

logger = logging.getLogger(__name__)


def get_teacher_review_with_names_query(db: Session):
    """
    Returns a SQLAlchemy query object with JOINs to retrieve teacher and student names.
    """
    teacher_user = User.__table__.alias("teacher_user")
    student_user = User.__table__.alias("student_user")

    return (
        select(
            TeacherReview.review_id.label("id"), 
            teacher_user.c.full_name.label("teacher_name"),
            student_user.c.full_name.label("student_name"),
            TeacherReview.rating,
            TeacherReview.review_date,
            TeacherReview.review_content
        )
        .select_from(
            join(
                TeacherReview,
                teacher_user,
                TeacherReview.teacher_user_id == teacher_user.c.user_id
            )
        )
        .join(
            student_user,
            TeacherReview.student_user_id == student_user.c.user_id
        )
    )

def get_teacher_review(db: Session, review_id: int):
    """Get teacher review by ID, returning a TeacherReviewView object."""
    query = get_teacher_review_with_names_query(db).where(TeacherReview.review_id == review_id)
    result = db.execute(query).first()
    if result:
        return TeacherReviewView.model_validate(result)
    return None

def get_teacher_reviews_by_teacher_user_id(db: Session, teacher_user_id: int, skip: int = 0, limit: int = 100):
    """Get a list of reviews by teacher_user_id, returning a list of TeacherReviewView objects."""
    query = (
        get_teacher_review_with_names_query(db)
        .where(TeacherReview.teacher_user_id == teacher_user_id)
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(query).all()
    return [TeacherReviewView.model_validate(row) for row in results]

def get_teacher_reviews_by_student_user_id(db: Session, student_user_id: int, skip: int = 0, limit: int = 100):
    """Get a list of reviews by student_user_id, returning a list of TeacherReviewView objects."""
    query = (
        get_teacher_review_with_names_query(db)
        .where(TeacherReview.student_user_id == student_user_id)
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(query).all()
    return [TeacherReviewView.model_validate(row) for row in results]

# This function is already correct based on your previous code
def get_all_teacher_reviews(db: Session, skip: int = 0, limit: int = 100) -> List[TeacherReviewView]:
    """
    Query all teacher reviews, getting teacher and student names by JOINing with the users table.
    """
    query = get_teacher_review_with_names_query(db).offset(skip).limit(limit)
    results = db.execute(query).all()
    return [TeacherReviewView.model_validate(row) for row in results]

def create_teacher_review(
    db: Session, 
    teacher_review: TeacherReviewCreate, 
    student_user_id: int
) -> TeacherReview: 
    # Kiểm tra đã tồn tại review của student cho teacher này chưa
    existing_review = db.query(TeacherReview).filter(
        TeacherReview.teacher_user_id == teacher_review.teacher_user_id,
        TeacherReview.student_user_id == student_user_id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã đánh giá giáo viên này rồi."
        )

    db_teacher_review = TeacherReview(
        teacher_user_id=teacher_review.teacher_user_id,
        student_user_id=student_user_id,
        rating=teacher_review.rating,
        review_content=teacher_review.review_content,
        review_date=datetime.now()
    )
    db.add(db_teacher_review)
    db.commit()
    db.refresh(db_teacher_review)
    return db_teacher_review

def get_teacher_review_model(db: Session, review_id: int) -> TeacherReview | None:
    """
    Lấy đối tượng Model TeacherReview từ DB theo ID.
    Hàm này được dùng để kiểm tra quyền.
    """
    return db.get(TeacherReview, review_id)

def update_teacher_review(db: Session, db_obj: TeacherReview, obj_in: TeacherReviewUpdate):
    """Cập nhật thông tin review dựa trên db_obj."""
    update_data = obj_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_teacher_review(db: Session, db_obj: TeacherReview):
    db.delete(db_obj)
    db.commit()
    return db_obj
