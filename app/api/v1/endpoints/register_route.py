# app/api/endpoints/register.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import registration_service
from app.schemas.register_schema import (
    RegisterRequest,
    ParentAndChildrenRequest,
    RegisterStudentWithParentRequest,
)

router = APIRouter()

@router.post(
    "/single-user",
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký một người dùng duy nhất (teacher,...)"
)
def register_single_user(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý đăng ký một người dùng duy nhất dựa trên vai trò.
    Người dùng không được phép tự đăng ký với vai trò 'manager'.
    """
    if request.role == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không được phép tự đăng ký với vai trò 'manager'."
        )
    return registration_service.register_single_user_service(db, request)

@router.post(
    "/parent-and-children",
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký phụ huynh và một hoặc nhiều học sinh"
)
def register_parent_with_children(
    request: ParentAndChildrenRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý đăng ký một phụ huynh và một hoặc nhiều người con trong cùng một yêu cầu.
    """
    return registration_service.register_parent_with_children_service(db, request)

@router.post(
    "/student-with-existing-parent",
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký một học sinh và liên kết với một phụ huynh đã có"
)
def register_student_with_parent(
    request: RegisterStudentWithParentRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý đăng ký một học sinh mới và liên kết với một phụ huynh đã có.
    """
    return registration_service.register_student_with_existing_parent_service(db, request)
