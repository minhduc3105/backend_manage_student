# app/api/v1/endpoints/teacher_review_route.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.crud import teacher_review_crud
from app.crud import teacher_crud
from app.crud import student_crud
from app.schemas import teacher_review_schema
from app.api import deps
# Import các dependencies cần thiết từ auth.py
from app.api.auth.auth import get_current_active_user, has_roles
from app.models.user_model import User
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Dependency cho quyền truy cập của Student hoặc Parent
STUDENT_ONLY = has_roles(["student"])

MANAGER_AND_STUDENT = has_roles(["manager", "student"])

@router.post(
    "/",
    response_model=teacher_review_schema.TeacherReview, 
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một bản ghi đánh giá giáo viên mới",
    dependencies=[Depends(STUDENT_ONLY)] 
)
def create_new_teacher_review(
    teacher_review_in: teacher_review_schema.TeacherReviewCreate, 
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    # Kiểm tra teacher tồn tại
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_review_in.teacher_user_id)
    if not db_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Kiểm tra student có tồn tại không
    db_student = student_crud.get_student(db, user_id=current_user.user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Tạo review với student_user_id = current_user.user_id
    return teacher_review_crud.create_teacher_review(
        db=db, 
        teacher_review=teacher_review_in, 
        student_user_id=current_user.user_id
    )


@router.get(
    "",
    response_model=List[teacher_review_schema.TeacherReviewView],
    summary="Lấy danh sách tất cả đánh giá của giáo viên",
    dependencies=[Depends(get_current_active_user)] # Bất kỳ người dùng đã đăng nhập nào cũng có thể xem
)
def get_all_reviews(
    db: Session = Depends(deps.get_db), 
    skip: int = 0, 
    limit: int = 100
):
    """
    Lấy tất cả các đánh giá của giáo viên.
    
    Quyền truy cập: **all authenticated users**
    """
    reviews = teacher_review_crud.get_all_teacher_reviews(db, skip, limit)
    if not reviews:
        # Tùy chọn: trả về 404 nếu không tìm thấy đánh giá nào
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đánh giá nào."
        )
    return reviews


@router.get(
    "/{review_id}", 
    response_model=teacher_review_schema.TeacherReviewView,
    summary="Lấy thông tin một đánh giá giáo viên theo ID",
    dependencies=[Depends(get_current_active_user)] # Bất kỳ người dùng đã đăng nhập nào cũng có thể xem
)
def get_teacher_review(
    review_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy thông tin một đánh giá giáo viên theo ID.
    
    Quyền truy cập: **all authenticated users**
    """
    db_teacher_review = teacher_review_crud.get_teacher_review(db, review_id=review_id)
    if db_teacher_review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Đánh giá giáo viên không tìm thấy."
        )
    return db_teacher_review

@router.get(
    "/by_teacher/{user_id}", 
    response_model=List[teacher_review_schema.TeacherReviewView],
    summary="Lấy tất cả đánh giá của một giáo viên theo user_id",
    dependencies=[Depends(get_current_active_user)] # Bất kỳ người dùng đã đăng nhập nào cũng có thể xem
)
def get_reviews_by_teacher(
    user_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy tất cả đánh giá của một giáo viên theo user_id.
    
    Quyền truy cập: **all authenticated users**
    """
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=user_id)
    if not db_teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher with id {user_id} not found."
        )
    
    reviews = teacher_review_crud.get_teacher_reviews_by_teacher_user_id(db, teacher_user_id=user_id)
    return reviews

@router.get(
    "/by_student/{user_id}", 
    response_model=List[teacher_review_schema.TeacherReviewView],
    summary="Lấy tất cả đánh giá của một giáo viên theo user_id",
    dependencies=[Depends(get_current_active_user)] # Bất kỳ người dùng đã đăng nhập nào cũng có thể xem
)
def get_reviews_by_student(
    user_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy tất cả đánh giá của một giáo viên theo user_id.
    
    Quyền truy cập: **all authenticated users**
    """
    db_student = student_crud.get_student(db, user_id=user_id)
    if not db_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"student with id {user_id} not found."
        )
    
    reviews = teacher_review_crud.get_teacher_reviews_by_student_user_id(db, student_user_id=user_id)
    return reviews

# PUT: Chỉ student sửa review của chính mình
@router.put(
    "/{review_id}", 
    response_model=teacher_review_schema.TeacherReview,
    summary="Cập nhật thông tin một đánh giá giáo viên theo ID",
    dependencies=[Depends(STUDENT_ONLY)]
)
def update_existing_teacher_review(
    review_id: int, 
    teacher_review_update: teacher_review_schema.TeacherReviewUpdate, 
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    # ✅ Lấy Model SQLAlchemy để kiểm tra quyền
    db_teacher_review_model = teacher_review_crud.get_teacher_review_model(db, review_id=review_id)
    
    if not db_teacher_review_model:
        raise HTTPException(status_code=404, detail="Đánh giá giáo viên không tìm thấy.")

    # ✅ Kiểm tra quyền trên đối tượng Model (chắc chắn có student_user_id)
    # Chỉ student sửa review của chính mình
    if db_teacher_review_model.student_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền sửa đánh giá này."
        )

    updated_review = teacher_review_crud.update_teacher_review(
        db=db, 
        db_obj=db_teacher_review_model, # Truyền Model vào hàm update
        obj_in=teacher_review_update
    )
    return updated_review


# DELETE: Manager hoặc student xóa
@router.delete(
    "/{review_id}", 
    status_code=status.HTTP_200_OK,
    summary="Xóa một đánh giá giáo viên theo ID",
    dependencies=[Depends(MANAGER_AND_STUDENT)]
)
def delete_teacher_review_api(
    review_id: int, 
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    # ✅ Lấy Model SQLAlchemy để kiểm tra quyền
    db_teacher_review_model = teacher_review_crud.get_teacher_review_model(db, review_id=review_id)
    
    if not db_teacher_review_model:
        raise HTTPException(status_code=404, detail="Đánh giá giáo viên không tìm thấy.")

    # ✅ Kiểm tra quyền trên đối tượng Model (chắc chắn có student_user_id)
    # Nếu student, chỉ được xóa review của chính mình
    if "student" in current_user.roles and db_teacher_review_model.student_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa đánh giá này."
        )

    deleted_review = teacher_review_crud.delete_teacher_review(db=db, db_obj=db_teacher_review_model)
    return {
        "message": "Đánh giá giáo viên đã được xóa thành công.",
        "deleted_review_id": deleted_review.review_id,
        "status": "success"
    }