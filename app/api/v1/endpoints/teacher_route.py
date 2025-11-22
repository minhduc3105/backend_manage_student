# app/api/v1/endpoints/teacher_route.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

# CRUD
from app.crud import teacher_crud
from app.crud import user_crud
from app.crud import user_role_crud # cần import CRUD user_role

# Schemas
from app.schemas import teacher_schema
from app.schemas.user_role_schema import UserRoleCreate

# Dependencies
from app.api import deps
# Import dependency factory
from app.api.auth.auth import get_current_active_user, has_roles
from app.schemas.auth_schema import AuthenticatedUser
from app.schemas import student_schema, class_schema

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Dependency cho quyền truy cập của Manager hoặc Teacher
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])


@router.post(
    "/",
    response_model=teacher_schema.Teacher,
    status_code=status.HTTP_201_CREATED,
    summary="Gán vai trò giáo viên cho một người dùng đã tồn tại",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền gán vai trò
)
def assign_teacher(
    teacher_in: teacher_schema.TeacherCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Gán vai trò giáo viên cho một user đã tồn tại bằng cách tạo một bản ghi mới trong bảng teachers.
    Các trường bắt buộc: user_id, base_salary_per_class, reward_bonus.

    Quyền truy cập: **manager**
    """
    # 1. Kiểm tra user có tồn tại
    db_user = user_crud.get_user(db=db, user_id=teacher_in.user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {teacher_in.user_id} not found."
        )

    # 2. Kiểm tra user đã là teacher chưa
    existing_teacher = teacher_crud.get_teacher_by_user_id(db, user_id=teacher_in.user_id)
    if existing_teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id {teacher_in.user_id} is already a teacher."
        )

    # 3. Gán teacher bằng cách sử dụng trực tiếp dữ liệu từ request
    db_teacher = teacher_crud.create_teacher(db=db, teacher_in=teacher_in)

    # 4. Cập nhật user_roles nếu chưa có role "teacher"
    existing_role = user_role_crud.get_user_role(db, user_id=teacher_in.user_id, role_name="teacher")
    if not existing_role:
        user_role_crud.create_user_role(
            db=db,
            role_in=UserRoleCreate(
                user_id=teacher_in.user_id,
                role_name="teacher",
                assigned_at=datetime.utcnow()
            )
        )

    return db_teacher


@router.get(
    "/", 
    response_model=List[teacher_schema.Teacher],
    summary="Lấy danh sách tất cả giáo viên",
    dependencies=[Depends(MANAGER_OR_TEACHER)] # Manager và teacher có thể xem
)
def get_all_teachers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy danh sách tất cả giáo viên.
    
    Quyền truy cập: **manager**, **teacher**
    """
    return teacher_crud.get_all_teachers(db, skip=skip, limit=limit)


@router.get(
    "/{teacher_user_id}", 
    response_model=teacher_schema.Teacher,
    summary="Lấy thông tin một giáo viên theo ID",
    dependencies=[Depends(MANAGER_OR_TEACHER)] # Manager và teacher có thể xem
)
def get_teacher(
    teacher_user_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy thông tin một giáo viên theo ID.
    
    Quyền truy cập: **manager**, **teacher**
    """
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if db_teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Giáo viên không tìm thấy."
        )
    return db_teacher


@router.put(
    "/{teacher_user_id}", 
    response_model=teacher_schema.Teacher,
    summary="Cập nhật thông tin giáo viên theo ID",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền cập nhật
)
def update_existing_teacher(
    teacher_user_id: int, 
    teacher: teacher_schema.TeacherUpdate, 
    db: Session = Depends(deps.get_db)
):
    """
    Cập nhật thông tin giáo viên theo ID.
    
    Quyền truy cập: **manager**
    """
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if db_teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Giáo viên không tìm thấy."
        )

    updated_teacher = teacher_crud.update_teacher(db, db_obj=db_teacher, obj_in=teacher)
    return updated_teacher


@router.delete(
    "/{teacher_user_id}", 
    response_model=dict,
    summary="Xóa một giáo viên",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền xóa
)
def delete_existing_teacher(
    teacher_user_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Xóa một giáo viên khỏi cơ sở dữ liệu.
    
    Quyền truy cập: **manager**
    """
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if db_teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy giáo viên."
        )

    deleted_teacher = teacher_crud.delete_teacher(db, db_obj=db_teacher)

    return {
        "deleted_teacher": teacher_schema.Teacher.from_orm(deleted_teacher).dict(),
        "deleted_at": datetime.utcnow().isoformat(),
        "status": "success"
    }

@router.get(
    "/{teacher_user_id}/stats",
    response_model=teacher_schema.TeacherStats,
    summary="Lấy số liệu thống kê của giáo viên",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_teacher_stats(
    teacher_user_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Lấy các số liệu thống kê chi tiết của một giáo viên, bao gồm số lớp đã dạy, số lịch trình, số đánh giá và điểm trung bình.

    Quyền truy cập: **manager**, **teacher**
    """
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if not db_teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Giáo viên không tìm thấy."
        )
    return teacher_crud.get_teacher_stats(db, teacher_user_id=teacher_user_id)

@router.get(
    "/{teacher_user_id}/classes",
    response_model=List[teacher_schema.ClassTaught],
    summary="Lấy danh sách các lớp học của một giáo viên",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_teacher_classes(
    teacher_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy danh sách các lớp học mà một giáo viên đang phụ trách.
    - Manager: có thể xem lớp học của bất kỳ giáo viên nào.
    - Teacher: chỉ có thể xem lớp học của chính mình.
    
    Quyền truy cập: **manager**, **teacher**
    """
    if "teacher" in current_user.roles and current_user.user_id != teacher_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem lớp học của giáo viên khác."
        )

    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if not db_teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Giáo viên có ID {teacher_user_id} không tồn tại."
        )

    return teacher_crud.get_class_taught(db, teacher_user_id=teacher_user_id)

@router.get(
    "/{teacher_user_id}/students",
    response_model=List[class_schema.Student], # Sử dụng schema Student để trả về
    summary="Lấy danh sách các học sinh do một giáo viên phụ trách",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_teacher_students_list(
    teacher_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy danh sách tất cả các học sinh đang theo học các lớp do giáo viên này phụ trách. 
    Danh sách học sinh được loại bỏ trùng lặp.

    - **Manager**: có thể xem danh sách học sinh của bất kỳ giáo viên nào.
    - **Teacher**: chỉ có thể xem danh sách học sinh của **chính mình**.
    
    Quyền truy cập: **manager**, **teacher**
    """
    
    # 1. Kiểm tra quyền truy cập (Giáo viên chỉ được xem của chính mình)
    if "teacher" in current_user.roles and current_user.user_id != teacher_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem danh sách học sinh của giáo viên khác."
        )

    # 2. Kiểm tra giáo viên có tồn tại
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=teacher_user_id)
    if not db_teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Giáo viên có ID {teacher_user_id} không tồn tại."
        )

    # 3. Sử dụng hàm get_teacher_students (giả định đã được thêm vào teacher_crud)
    try:
        students = teacher_crud.get_teacher_students(db, teacher_user_id=teacher_user_id)
    except Exception as e:
        # Xử lý lỗi nếu có vấn đề xảy ra trong quá trình truy vấn
        print(f"Error fetching students for teacher {teacher_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi khi lấy danh sách học sinh."
        )
        
    return students