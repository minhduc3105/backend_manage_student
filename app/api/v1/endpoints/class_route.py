# app/api/endpoints/class.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.api.deps import get_db
from app.api.auth.auth import AuthenticatedUser, get_current_active_user, has_roles
from app.crud import class_crud
from app.schemas import class_schema
from app.services.excel_services.export_class import export_class
from app.api import deps
from app.schemas import teacher_schema
from app.crud import teacher_crud

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Dependency cho quyền truy cập của Manager hoặc Teacher
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])

MANAGER_OR_TEACHER_OR_STUDENT = has_roles(["manager","teacher", "student"])

# Tạo lớp học mới
@router.post(
    "",
    response_model=class_schema.Class,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một lớp học mới"
)
def create_new_class(
    class_in: class_schema.ClassCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_ONLY)
):
    """
    Tạo một lớp học mới.
    
    Quyền truy cập: **manager**
    """
    db_class = class_crud.get_class_by_name(db, class_name=class_in.class_name)
    if db_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên lớp học đã tồn tại."
        )
    return class_crud.create_class(db=db, class_data=class_in)

# Cập nhật thông tin lớp học
@router.put(
    "/{class_id}",
    response_model=class_schema.Class,
    summary="Cập nhật thông tin của một lớp học"
)
def update_existing_class(
    class_id: int,
    class_update: class_schema.ClassUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_ONLY)
):
    """
    Cập nhật thông tin của một lớp học cụ thể bằng ID.
    
    Quyền truy cập: **manager**
    """
    db_class = class_crud.update_class(db, class_id=class_id, class_update=class_update)
    if db_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lớp học không tìm thấy."
        )
    return db_class

# Xóa lớp học
@router.delete(
    "/{class_id}",
    response_model=dict,
    summary="Xóa một lớp học"
)
def delete_existing_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_ONLY)
):
    """
    Xóa một lớp học cụ thể bằng ID.
    
    Quyền truy cập: **manager**
    """
    db_class = class_crud.get_class(db, class_id=class_id)
    if db_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lớp học không tìm thấy."
        )
    deleted_class = class_crud.delete_class(db, class_id=class_id)
    return {
        "deleted_class": class_schema.Class.from_orm(deleted_class).dict(),
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "status": "success"
    }

# Lấy danh sách tất cả các lớp học
@router.get(
    "",
    response_model=List[class_schema.ClassView],
    summary="Lấy danh sách các lớp học theo quyền",
    dependencies=[Depends(MANAGER_OR_TEACHER_OR_STUDENT)]
)
def get_all_classes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy danh sách các lớp học dựa trên vai trò của người dùng.
    - **Manager**: Trả về tất cả các lớp.
    - **Teacher**: Chỉ trả về các lớp mà giáo viên đó phụ trách.
    - **Student**: Chỉ trả về các lớp mà sinh viên đó đã đăng ký và còn đang học.
    
    Quyền truy cập: **manager**, **teacher**, **student**
    """
    if "manager" in current_user.roles:
        classes = class_crud.get_all_classes(db, skip=skip, limit=limit)
    elif "teacher" in current_user.roles:
        classes = class_crud.get_classes_by_teacher_user_id(db, teacher_user_id=current_user.user_id, skip=skip, limit=limit)
    elif "student" in current_user.roles:
        classes = class_crud.get_active_classes_by_student_user_id(db, student_user_id=current_user.user_id, skip=skip, limit=limit)
    else:
        classes = []

    return classes

# Lấy thông tin của một lớp học
@router.get(
    "/{class_id}",
    response_model=class_schema.ClassView,
    summary="Lấy thông tin của một lớp học"
)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_OR_TEACHER)
):
    """
    Lấy thông tin của một lớp học cụ thể bằng ID.
    
    Quyền truy cập: **manager**, **teacher**
    """
    db_class = class_crud.get_class(db, class_id=class_id)
    if db_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lớp học không tìm thấy."
        )
    return db_class

# Xuất danh sách lớp học ra file Excel
@router.get(
    "/export/{class_id}",
    summary="Xuất danh sách lớp học ra file Excel"
)
def export_class_excel(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_OR_TEACHER)
):
    """
    Xuất danh sách sinh viên của một lớp học ra file Excel.
    
    Quyền truy cập: **manager**, **teacher**
    """
    return export_class(db, class_id)

@router.get(
    "/{class_id}/students",
    response_model=List[class_schema.Student],
    summary="Lấy danh sách học sinh của một lớp"
)
def get_students_of_class(
    class_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(MANAGER_OR_TEACHER)
):
    """
    Lấy danh sách học sinh của lớp `class_id`.
    
    Quyền truy cập: **manager**, **teacher**
    """
    students = class_crud.get_students_list(db, class_id=class_id, skip=skip, limit=limit)
    if not students:
        # không raise 404 mà trả [] cho client dễ xử lý hơn
        return []
    return students