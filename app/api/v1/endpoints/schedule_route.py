from app.models.schedule_model import DayOfWeekEnum, ScheduleTypeEnum
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as dt_date

# CRUD & Schemas
from app.crud import schedule_crud, student_crud
from app.schemas import schedule_schema

# Deps & Auth
from app.api import deps
from app.api.auth.auth import AuthenticatedUser, get_current_active_user, has_roles

# Services
from app.services import schedule_service, user_service
from app.api.v1.endpoints.enrollment_route import MANAGER_ONLY

router = APIRouter()

# Dependency shortcut
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])


@router.post(
    "/",
    response_model=schedule_schema.Schedule,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def create_schedule_route(
    schedule_in: schedule_schema.ScheduleCreate,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Tạo một lịch trình mới.
    Chỉ Manager hoặc Teacher được phép.
    """
    return schedule_crud.create_schedule(
        db=db,
        schedule_in=schedule_in,
        current_user=current_user
    )

@router.get("/", response_model=List[schedule_schema.ScheduleView])
def get_all_schedules_route(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    dependencies=[Depends(MANAGER_ONLY)]
):
    """
    Lấy danh sách tất cả lịch trình, có phân trang.
    """
    return schedule_crud.search_schedules(
        db=db,
        skip=skip,
        limit=limit,
        class_id=None,
        class_ids=None,
        day_of_week=None,
        schedule_type=None,
        date=None,
        room=None
    )

@router.get("/search", response_model=List[schedule_schema.ScheduleView])
def search_schedules_route(
    db: Session = Depends(deps.get_db),
    class_id: Optional[int] = Query(None),
    schedule_type: Optional[ScheduleTypeEnum] = Query(None),
    day_of_week: Optional[DayOfWeekEnum] = Query(None),
    date: Optional[dt_date] = Query(None),
    room: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Tìm kiếm lịch trình với nhiều điều kiện lọc.
    """
    return schedule_service.search_schedules_by_user_role(
        db=db,
        current_user=current_user,
        class_id=class_id,
        schedule_type=schedule_type,
        day_of_week=day_of_week,
        date=date,
        room=room
    )


@router.get("/{schedule_id}", response_model=schedule_schema.ScheduleView)
def get_schedule_route(
    schedule_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Xem chi tiết lịch trình.
    Manager/Teacher xem được mọi lịch.
    Student xem được lịch của lớp mình.
    """
    db_schedule = schedule_crud.get_schedule_by_id(db, schedule_id=schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Lịch trình không tìm thấy.")

    # Kiểm tra quyền truy cập (logic này có thể cần được refactor vào service layer)
    # Tuy nhiên, để đáp ứng yêu cầu, ta sẽ giữ lại logic hiện tại.
    # schedule_crud.get_schedule_by_id đã trả về ScheduleView, nên không còn thuộc tính `class_.students`
    if "manager" in current_user.roles or "teacher" in current_user.roles:
        return db_schedule

    # Lấy class_ids của học sinh
    student_class_ids = schedule_crud.get_class_ids_for_student(db, current_user.user_id)
    if db_schedule.class_name in [c.class_name for c in schedule_crud.get_classes_by_teacher_user_id(db, current_user.user_id)]:
        return db_schedule

    raise HTTPException(status_code=403, detail="Bạn không có quyền xem lịch này.")


@router.put(
    "/{schedule_id}",
    response_model=schedule_schema.Schedule,
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def update_existing_schedule_route(
    schedule_id: int,
    schedule_update: schedule_schema.ScheduleUpdate,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Cập nhật lịch trình (partial update).
    Chỉ cần truyền những field muốn đổi, bao gồm cả class_id nếu cần.
    """
    db_schedule = schedule_crud.get_schedule(db, schedule_id=schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Lịch trình không tìm thấy.")

    return schedule_crud.update_schedule(db, schedule=db_schedule, schedule_in=schedule_update)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_roles(["manager"]))]
)
def delete_existing_schedule_route(
    schedule_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Xóa lịch trình.
    Chỉ Manager được phép.
    """
    db_schedule = schedule_crud.get_schedule(db, schedule_id=schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Lịch trình không tìm thấy.")

    schedule_crud.delete_schedule(db, schedule=db_schedule)
    return


@router.get("/teachers/{teacher_id}", response_model=List[schedule_schema.ScheduleView])
def get_teacher_schedules_route(
    teacher_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy lịch trình của giáo viên.
    Manager hoặc chính giáo viên đó mới được xem.
    """
    teacher_user_id = user_service.get_user_id(db, "teacher", teacher_id)

    if "manager" not in current_user.roles and current_user.user_id != teacher_user_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem lịch giáo viên này.")

    return schedule_service.get_schedules_for_teacher(db=db, teacher_id=teacher_id)


@router.get("/students/{student_user_id}", response_model=List[schedule_schema.ScheduleView])
def get_student_schedules_route(
    student_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy lịch trình của học sinh.
    Manager, phụ huynh hoặc chính học sinh đó mới được xem.
    """
    student_user_id = user_service.get_user_id(db, "student", student_user_id)
    db_student = student_crud.get_student(db, student_user_id)

    is_manager = "manager" in current_user.roles
    is_student_self = current_user.user_id == student_user_id
    is_parent_of_student = (
        db_student and db_student.parent and db_student.parent.user_id == current_user.user_id
    )

    if not (is_manager or is_student_self or is_parent_of_student):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem lịch học sinh này.")

    return schedule_service.get_schedules_for_student(db=db, student_user_id=student_user_id)
