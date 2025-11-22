from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.crud import payroll_crud, teacher_crud
from app.schemas import payroll_schema
from app.api import deps
from app.services import payroll_service
from app.api.auth.auth import get_current_active_user, has_roles
from app.api.v1.endpoints.evaluation_route import MANAGER_OR_TEACHER
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()
MANAGER_ONLY = has_roles(["manager"])

@router.post(
    "/",
    response_model=payroll_schema.Payroll,
    dependencies=[Depends(MANAGER_ONLY)]
)
def create_new_payroll(
    payroll_in: payroll_schema.PayrollCreate,
    db: Session = Depends(deps.get_db)
):
    teacher = teacher_crud.get_teacher(db, payroll_in.teacher_user_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return payroll_service.create_payroll(db, teacher, payroll_in)

@router.get(
    "/",
    response_model=List[payroll_schema.PayrollView],
    summary="Lấy danh sách bảng lương",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_all_payrolls(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Lấy danh sách các bản ghi bảng lương.
    - Nếu người dùng là **manager**, trả về tất cả bảng lương.
    - Nếu người dùng là **teacher**, chỉ trả về bảng lương của chính họ.

    Quyền truy cập: **manager**, **teacher**
    """
    if "teacher" in current_user.roles:
        payrolls = payroll_crud.get_payrolls_by_teacher(
            db,
            teacher_user_id=current_user.user_id,
            skip=skip,
            limit=limit
        )
    else: # Manager or other roles with access
        payrolls = payroll_crud.get_all_payrolls(db, skip=skip, limit=limit)
        
    return [
        payroll_schema.PayrollView(
            id=p.payroll_id,
            month=p.month,
            teacher=fullname,
            base_salary=p.total_base_salary,
            bonus=p.reward_bonus,
            total=p.total,
            status=p.status,
            sent_at=p.sent_at
        )
        for p, fullname in payrolls
    ]


@router.post(
    "/run_payrolls",
    response_model=List[payroll_schema.Payroll], 
    dependencies=[Depends(MANAGER_ONLY)]
)
def run_payrolls(
    db: Session = Depends(deps.get_db)
):
    try:
        results = payroll_service.run_monthly_payroll(db)
        return results # Trả về list of payroll objects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during payroll processing: {str(e)}"
        )

@router.get("/{payroll_id}", response_model=payroll_schema.PayrollView)
def get_payroll(
    payroll_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    # Sử dụng hàm CRUD mới để lấy dữ liệu
    payroll_data = payroll_crud.get_payroll(db, payroll_id)

    if not payroll_data:
        raise HTTPException(status_code=404, detail="Payroll not found")

    db_payroll, teacher_fullname = payroll_data

    # Kiểm tra quyền truy cập của người dùng hiện tại
    # Manager có quyền xem tất cả
    if "manager" in current_user.roles:
        return payroll_schema.PayrollView(
            id=db_payroll.payroll_id,
            month=db_payroll.month,
            teacher=teacher_fullname,
            base_salary=db_payroll.total_base_salary,
            bonus=db_payroll.reward_bonus,
            total=db_payroll.total,
            status=db_payroll.status,
            sent_at=db_payroll.sent_at
        )

    # Nếu không phải manager, chỉ giáo viên liên quan mới xem được
    if db_payroll.teacher_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this payroll")
    
    # Trả về đối tượng PayrollView nếu được phép
    return payroll_schema.PayrollView(
        id=db_payroll.payroll_id,
        teacher=teacher_fullname,
        base_salary=db_payroll.total_base_salary,
        bonus=db_payroll.reward_bonus,
        total=db_payroll.total,
        status=db_payroll.status,
        sent_at=db_payroll.sent_at
    )

@router.put(
    "/{payroll_id}",
    response_model=payroll_schema.Payroll,
    dependencies=[Depends(MANAGER_ONLY)]
)
def update_payroll_endpoint(
    payroll_id: int,
    payroll_update: payroll_schema.PayrollUpdate,
    db: Session = Depends(deps.get_db)
):
    return payroll_service.update_payroll_with_notification(db, payroll_id, payroll_update)

@router.delete(
    "/{payroll_id}",
    status_code=status.HTTP_204_NO_CONTENT, # Sử dụng 204 No Content cho delete thành công
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_existing_payroll(
    payroll_id: int,
    db: Session = Depends(deps.get_db)
):
    db_payroll = payroll_crud.get_payroll(db, payroll_id)
    if not db_payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    payroll_crud.delete_payroll(db, payroll_id)
    return

@router.get("/teacher/{teacher_user_id}", response_model=List[payroll_schema.PayrollView])
def get_teacher_payrolls(
    teacher_user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    teacher = teacher_crud.get_teacher(db, teacher_user_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if "manager" not in current_user.roles and teacher.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this teacher's payrolls")

    payrolls = payroll_crud.get_payrolls_by_teacher(db, teacher_user_id, skip=skip, limit=limit)
    if not payrolls:
        raise HTTPException(status_code=404, detail="No payrolls found for this teacher")

    return [
        payroll_schema.PayrollView(
            id=p.payroll_id,
            teacher=fullname,
            month=p.month,
            base_salary=p.total_base_salary,
            bonus=p.reward_bonus,
            total=p.total,
            status=p.status,
            sent_at=p.sent_at
        )
        for p, fullname in payrolls
    ]
