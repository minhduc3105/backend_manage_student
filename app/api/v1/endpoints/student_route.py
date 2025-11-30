from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api.auth.auth import get_current_active_user, has_roles
from app.api import deps
from app.crud import student_crud, user_crud, user_role_crud
from app.schemas.user_role_schema import UserRoleCreate
from app.schemas import student_schema
from app.schemas import class_schema
from app.schemas.stats_schema import StudentStats
from app.crud import parent_crud
from app.models.user_model import User
from app.schemas.teacher_schema import TeacherView
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()

MANAGER_ONLY = has_roles(["manager"])
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])
BASE_USERS=has_roles(["manager", "teacher", "student", "parent"])

# --- ASSIGN student (gán user thành student) ---
@router.post(
    "/",
    response_model=student_schema.Student,
    status_code=status.HTTP_201_CREATED,
    summary="Gán một user đã tồn tại thành student",
    dependencies=[Depends(MANAGER_ONLY)]
)
def assign_student(
    student_in: student_schema.StudentCreate,
    db: Session = Depends(deps.get_db)
):
    # Kiểm tra user tồn tại
    db_user = user_crud.get_user(db=db, user_id=student_in.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail=f"User with id {student_in.user_id} not found.")

    # Kiểm tra user đã là student chưa
    existing_student = student_crud.get_student_by_user_id(db=db, user_id=student_in.user_id)
    if existing_student:
        raise HTTPException(status_code=400, detail=f"User with id {student_in.user_id} is already a student.")

    # Gán student
    db_student = student_crud.create_student(
        db=db,
        student_in=student_schema.StudentCreate(
            user_id=student_in.user_id,
            parent_id=student_in.parent_id
        )
    )

    # Cập nhật user_roles nếu chưa có role "student"
    existing_role = user_role_crud.get_user_role(db, user_id=student_in.user_id, role_name="student")
    if not existing_role:
        user_role_crud.create_user_role(
            db=db,
            role_in=UserRoleCreate(
                user_id=student_in.user_id,
                role_name="student",
                assigned_at=datetime.utcnow()
            )
        )

    return db_student


# --- GET all students ---
@router.get(
        "/",
    response_model=List[student_schema.StudentView], 
    summary="Lấy danh sách tất cả học sinh (Phân quyền theo Manager/Teacher)",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_all_students(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user) # Lấy user hiện tại
):
    """
    - **Manager**: Trả về tất cả học sinh.
    - **Teacher**: Chỉ trả về học sinh thuộc các lớp do giáo viên đó dạy.
"""
    teacher_user_id: Optional[int] = None

    # Nếu người dùng là Teacher (và không phải Manager)
    if "teacher" in current_user.roles and "manager" not in current_user.roles:
        teacher_user_id = current_user.user_id

    # Gọi hàm CRUD đã được cập nhật
    students_view = student_crud.get_students_for_role(
        db, 
        teacher_user_id=teacher_user_id, 
        skip=skip, 
        limit=limit
    )

    # Xử lý trường hợp không tìm thấy học sinh cho giáo viên đó
    if not students_view and teacher_user_id:
        # Có thể trả về 200 [] hoặc 404 tùy ý, 200 là tốt hơn cho danh sách rỗng
        return [] 
        
    return students_view


# --- GET student by ID ---
@router.get(
    "/{student_user_id}",
    response_model=student_schema.StudentView,
    summary="Lấy thông tin của một học sinh cụ thể",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_student(student_user_id: int, db: Session = Depends(deps.get_db)):
    db_student = student_crud.get_student(db, student_user_id=student_user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Học sinh không tìm thấy.")
    return db_student


# --- UPDATE student ---
@router.put(
    "/{user_id}",
    response_model=student_schema.Student,
    summary="Cập nhật thông tin của một học sinh",
    dependencies=[Depends(MANAGER_ONLY)]
)
def update_student(user_id: int, student_update: student_schema.StudentUpdate, db: Session = Depends(deps.get_db)):
    db_student = student_crud.update_student(db, user_id=user_id, student_update=student_update)
    if not db_student:
        raise HTTPException(status_code=404, detail="Học sinh không tìm thấy.")
    return db_student


# --- DELETE student ---
@router.delete(
    "/{user_id}",
    response_model=dict,
    summary="Xóa một học sinh",
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_student(user_id: int, db: Session = Depends(deps.get_db)):
    db_student = student_crud.get_student(db, user_id=user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Học sinh không tìm thấy.")

    deleted_student = student_crud.delete_student(db, user_id=user_id)
    return {
        "deleted_student": student_schema.Student.from_orm(deleted_student).dict(),
        "deleted_at": datetime.utcnow().isoformat(),
        "status": "success"
    }

@router.get(
    "/{user_id}/stats",
    response_model=StudentStats,
    summary="Lấy các chỉ số thống kê của một học sinh (GPA, điểm học tập/kỷ luật, số lớp)",
    # dependencies=[Depends(MANAGER_OR_TEACHER)] # Hoặc tùy chỉnh quyền truy cập
)
def get_student_stats(user_id: int, db: Session = Depends(deps.get_db)):
    # 1. Kiểm tra học sinh tồn tại
    db_student = student_crud.get_student(db, student_user_id=user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Học sinh không tìm thấy.")
    
    # 2. Lấy thống kê
    # Vì hàm CRUD không còn là async, ta gọi trực tiếp
    stats = student_crud.get_student_stats(db, student_user_id=user_id)
    
    return stats

@router.get(
    "/{user_id}/classes",
    response_model=List[class_schema.ClassView], # SỬ DỤNG CLASSVIEW
    summary="Lấy danh sách các lớp học đang 'active' mà học sinh đã đăng ký",
    dependencies=[Depends(MANAGER_OR_TEACHER)] # Cả Manager và Teacher đều có thể xem
)
def get_student_active_classes_endpoint(
    user_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy danh sách các lớp học hiện tại (trạng thái enrollment là 'active') mà học sinh đang tham gia.
    
    Quyền truy cập: **manager**, **teacher**
    """
    # 1. Kiểm tra học sinh tồn tại
    db_student = student_crud.get_student(db, user_id=user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Học sinh không tìm thấy.")

    # 2. Gọi hàm CRUD
    active_classes = student_crud.get_student_active_classes(db, student_user_id=user_id)
    
    return active_classes

async def authorize_student_view(
    student_user_id: int, 
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(BASE_USERS) 
):
    # Manager có thể xem bất kỳ ai
    if any(role in current_user.roles for role in ["manager"]):
        return student_user_id

    # Student chỉ có thể xem của chính mình
    if "student" in current_user.roles:
        if current_user.user_id != student_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Học sinh chỉ được phép xem thông tin của chính mình."
            )
        return student_user_id

    # Parent chỉ có thể xem của con mình
    if "parent" in current_user.roles:
        # Kiểm tra xem student_user_id có phải là con của parent_id hiện tại không
        is_child = parent_crud.is_child(db, student_id=student_user_id, parent_id=current_user.user_id)
        
        if not is_child:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phụ huynh chỉ được phép xem thông tin của con cái họ."
            )
        return student_user_id

    # Nếu không phải các vai trò trên hoặc không thỏa mãn điều kiện
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập.")

@router.get(
    "/{student_user_id}/teachers",
    response_model=List[TeacherView],
    summary="Lấy danh sách các giáo viên của một học sinh",
)
def get_student_teachers_endpoint(
    student_user_id: int = Depends(authorize_student_view), 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy danh sách giáo viên của học sinh (những người đã từng dạy học sinh này qua các lớp học).
    Quyền truy cập: **manager, teacher** (toàn bộ), **student** (của mình), **parent** (của con).
    """
    # 1. Kiểm tra học sinh tồn tại (Hàm authorize_student_view không kiểm tra sự tồn tại)
    db_student = student_crud.get_student(db, student_user_id)
    if not db_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Học sinh không tìm thấy.")

    # 2. Gọi hàm CRUD để lấy danh sách giáo viên
    teachers_list = student_crud.get_student_teachers(db, student_user_id=student_user_id)
    
    # 3. Trả về kết quả
    return teachers_list