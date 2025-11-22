from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.auth.auth import has_roles
from app.api.deps import get_db
from app.crud import enrollment_crud
from app.crud import student_crud, class_crud
from app.schemas.enrollment_schema import EnrollmentCreate, EnrollmentUpdate, Enrollment, EnrollmentView

router = APIRouter()

MANAGER_ONLY = has_roles(["manager"])
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])

# --- Manager only endpoints ---
@router.post(
    "/",
    response_model=Enrollment,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một bản ghi enrollment mới cho một sinh viên vào một lớp học",
    dependencies=[Depends(MANAGER_ONLY)]
)
def create_new_enrollment(
    enrollment_in: EnrollmentCreate,
    db: Session = Depends(get_db)
):
    # Kiểm tra student & class tồn tại
    student = student_crud.get_student(db, enrollment_in.student_user_id)
    cls = class_crud.get_class(db, enrollment_in.class_id)
    if not student or not cls:
        raise HTTPException(status_code=404, detail="Student or Class not found")

    # Kiểm tra enrollment đã tồn tại
    existing = enrollment_crud.get_enrollment(db, student_user_id=enrollment_in.student_user_id, class_id=enrollment_in.class_id)
    if existing:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this class.")

    enrollment = enrollment_crud.create_enrollment(db, enrollment_in=enrollment_in)
    return enrollment


@router.delete(
    "/{student_user_id}/{class_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cập nhật trạng thái enrollment của một sinh viên thành 'Inactive'",
    dependencies=[Depends(MANAGER_ONLY)]
)
def remove_enrollment(
    student_user_id: int,
    class_id: int,
    db: Session = Depends(get_db)
):
    removed = enrollment_crud.set_enrollment_inactive(db, student_user_id=student_user_id, class_id=class_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Enrollment record not found")
    return


# --- Manager or Teacher endpoints ---
@router.get(
    "/student/{student_user_id}",
    response_model=List[EnrollmentView],
    summary="Lấy danh sách các lớp học mà một sinh viên đã đăng ký",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_enrollments_for_student(student_user_id: int, db: Session = Depends(get_db)):
    enrollments = enrollment_crud.get_enrollments_by_student_user_id(db, student_user_id)
    if not enrollments:
        raise HTTPException(status_code=404, detail="Enrollments not found for this student")
    return enrollments


@router.get(
    "/class/{class_id}",
    response_model=List[EnrollmentView],
    summary="Lấy danh sách các sinh viên đã đăng ký vào một lớp học",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_active_enrollments_by_class(class_id: int, db: Session = Depends(get_db)):
    enrollments = enrollment_crud.get_active_enrollments_by_class_id(db, class_id)
    if not enrollments:
        raise HTTPException(status_code=404, detail="Enrollments not found for this class")
    return enrollments


# --- Manager only endpoint: get all ---
@router.get(
    "/",
    response_model=List[EnrollmentView],
    summary="Lấy tất cả các bản ghi enrollment",
    dependencies=[Depends(MANAGER_ONLY)]
)
def get_all_enrollments(db: Session = Depends(get_db)):
    enrollments = enrollment_crud.get_all_enrollments(db)
    if not enrollments:
        raise HTTPException(status_code=404, detail="No enrollments found")
    return enrollments


@router.put(
    "/{enrollment_id}",
    response_model=Enrollment,
    summary="Cập nhật thông tin enrollment",
    dependencies=[Depends(MANAGER_ONLY)]
)
def update_enrollment_endpoint(
    enrollment_id: int,
    enrollment_update: EnrollmentUpdate,
    db: Session = Depends(get_db)
):
    updated = enrollment_crud.update_enrollment(
        db, enrollment_id=enrollment_id, enrollment_update=enrollment_update.dict(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return updated