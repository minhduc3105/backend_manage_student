from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.attendance_schema import AttendanceRead, AttendanceBatchCreate, AttendanceUpdateLate
from app.services import attendance_service
from app.api.auth.auth import has_roles, get_current_active_user
from app.api.deps import get_db


router = APIRouter()
TEACHER_ONLY = has_roles(["teacher"])

@router.post(
    "/batch",
    response_model=list[AttendanceRead],
    dependencies=[Depends(TEACHER_ONLY)]
)
def create_attendance_records_for_class(
    attendance_data: AttendanceBatchCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user) 
):
    return attendance_service.create_batch_attendance(db, attendance_data, current_user)

@router.get("/all", response_model=List[AttendanceRead])
def get_all_attendances_auth_only_test(
    db: Session = Depends(get_db),
    schedule_id: int = None
):
    print("===== DEBUG ENTER =====")
    attendances = attendance_service.get_all_attendances_no_auth(db=db, schedule_id=schedule_id)
    print(f"Fetched {len(attendances)} records")
    return attendances


@router.get(
    "/{schedule_id}",
    response_model=List[AttendanceRead],
    dependencies=[Depends(TEACHER_ONLY)]
)
def get_attendance_records(
    schedule_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    return attendance_service.get_attendances(
        db,
        schedule_id=schedule_id,
        current_user=current_user,
    )

@router.patch(
    "/update_late",
    response_model=AttendanceRead,
    dependencies=[Depends(TEACHER_ONLY)]
)
def update_student_late_attendance(
    student_user_id: int,
    schedule_id: int,
    update_data: AttendanceUpdateLate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)  # thêm dòng này
):
    updated_record = attendance_service.update_late_attendance(
        db,
        student_user_id=student_user_id,
        schedule_id=schedule_id,
        checkin_time=update_data.checkin_time,
        attendance_date=update_data.attendance_date,
        current_user=current_user
    )
    if not updated_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi điểm danh để cập nhật.")
    return updated_record


@router.get(
    "/",
    response_model=List[AttendanceRead],
    dependencies=[Depends(TEACHER_ONLY)]
)
def get_all_attendances(
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    return attendance_service.get_attendances(db, current_user=current_user)


