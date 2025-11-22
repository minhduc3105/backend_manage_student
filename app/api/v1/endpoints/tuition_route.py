from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.schemas.tuition_schema import (
    TuitionCreate,
    TuitionUpdate,
    TuitionRead,
    TuitionView,
)
from app.services import tuition_service
from app.api.auth.auth import has_roles, get_current_active_user
from app.crud import tuition_crud
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()

# Dependency cho quyền truy cập
MANAGER_ONLY = has_roles(["manager"])
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])
MANAGER_OR_PARENT = has_roles(["manager", "parent"])
STUDENT_ONLY = has_roles(["student"])
PARENT_ONLY = has_roles(["parent"])
PARENT_OR_MANAGER = has_roles(["manager", "parent"])

@router.post(
    "/",
    response_model=TuitionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một bản ghi học phí mới",
    dependencies=[Depends(MANAGER_ONLY)]
)
def create_tuition(
    tuition_in: TuitionCreate, 
    db: Session = Depends(deps.get_db)
):
    """
    Tạo một bản ghi học phí mới và gửi thông báo cho phụ huynh.
    """
    return tuition_service.create_tuition_record(db, tuition_in)

@router.get(
    "/{tuition_id}",
    response_model=TuitionView,
    summary="Lấy thông tin học phí bằng ID",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_tuition_by_id(
    tuition_id: int, 
    db: Session = Depends(deps.get_db)
):
    tuition_data = tuition_crud.get_tuition(db, tuition_id)
    if not tuition_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuition not found")
        
    db_tuition, student_fullname = tuition_data
    
    return TuitionView(
        id=db_tuition.tuition_id,
        student=student_fullname,
        amount=db_tuition.amount,
        term=db_tuition.term,
        status=db_tuition.status,
        due_date=db_tuition.due_date
    )

# Sửa endpoint GET /
@router.get(
    "",
    response_model=List[TuitionView],
    summary="Lấy danh sách tất cả học phí",
    dependencies=[Depends(MANAGER_OR_PARENT)]
)
def list_tuitions(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    if "manager" in current_user.roles:
        results = tuition_crud.get_all_tuitions_with_student_name(db, skip=skip, limit=limit)
        tuition_views = []
        for tuition, student_fullname in results:
            tuition_views.append(TuitionView(
                id=tuition.tuition_id,
                student=student_fullname,
                amount=tuition.amount,
                term=tuition.term,
                status=tuition.status,
                due_date=tuition.due_date
            ))
        return tuition_views
    
    elif "parent" in current_user.roles:
        results = tuition_crud.get_tuitions_by_parent_user_id(db, parent_user_id=current_user.user_id, skip=skip, limit=limit)
        tuition_views = []
        for tuition, student_fullname in results:
            tuition_views.append(TuitionView(
                id=tuition.tuition_id,
                student=student_fullname,
                amount=tuition.amount,
                term=tuition.term,
                status=tuition.status,
                due_date=tuition.due_date
            ))
        return tuition_views

# Sửa endpoint GET /by_student/{student_user_id}
@router.get(
    "/by_student/{student_user_id}",
    response_model=List[TuitionView],
    summary="Lấy học phí theo student_user_id",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_tuitions_by_student_user_id(
    student_user_id: int,
    db: Session = Depends(deps.get_db)
):
    results = tuition_crud.get_tuitions_by_student_user_id(db, student_user_id=student_user_id)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy học phí cho học sinh này.")
    
    tuition_views = []
    for tuition, student_fullname in results:
        tuition_views.append(TuitionView(
            id=tuition.tuition_id,
            student=student_fullname,
            amount=tuition.amount,
            term=tuition.term,
            status=tuition.status,
            due_date=tuition.due_date
        ))
    return tuition_views

# Sửa endpoint GET /by_parent/{parent_id}
@router.get(
    "/by_parent/{parent_user_id}",
    response_model=List[TuitionView],
    summary="Lấy tất cả học phí theo parent",
    dependencies=[Depends(PARENT_OR_MANAGER)]
)
def get_tuitions_by_parent(
    parent_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    if "parent" in current_user.roles and "manager" not in current_user.roles:
        parent_user_id = current_user.user_id
    
    results = tuition_crud.get_tuitions_by_parent_user_id(db, parent_user_id=parent_user_id)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy học phí cho phụ huynh này.")
        
    tuition_views = []
    for tuition, student_fullname in results:
        tuition_views.append(TuitionView(
            id=tuition.tuition_id,
            student=student_fullname,
            amount=tuition.amount,
            status=tuition.status,
            due_date=tuition.due_date,
            term=tuition.term
        ))
    return tuition_views

@router.put(
    "/{tuition_id}",
    response_model=TuitionRead,
    summary="Cập nhật chi tiết học phí",
    dependencies=[Depends(MANAGER_ONLY)]
)
def update_tuition(
    tuition_id: int,
    tuition_in: TuitionUpdate,
    db: Session = Depends(deps.get_db)
):
    updated = tuition_crud.update_tuition(db, tuition_id, tuition_in)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuition not found hoặc đã thanh toán")
    return updated

@router.delete(
    "/{tuition_id}",
    summary="Xóa học phí",
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_tuition(
    tuition_id: int, 
    db: Session = Depends(deps.get_db)
):
    deleted = tuition_crud.delete_tuition(db, tuition_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuition not found")
    return {
        "message": "Bản ghi học phí đã được xóa thành công.",
        "status": "success"
    }


@router.post(
    "/generate-all",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sinh học phí cho tất cả học sinh",
    dependencies=[Depends(MANAGER_ONLY)]
)
def generate_tuition_for_all_students_route(
    background_tasks: BackgroundTasks,
    term: int = Query(..., gt=0, description="Kỳ học để tạo học phí"),
    due_date: date = Query(..., description="Hạn thanh toán"),
    db: Session = Depends(deps.get_db),  # dùng session từ FastAPI
):
    background_tasks.add_task(
        tuition_service.create_tuition_for_all_students,
        db=db,           # truyền session vào
        due_date=due_date,
        term=term
    )
    return {"message": "Đã chấp nhận yêu cầu. Quá trình tạo học phí đang chạy ngầm."}
