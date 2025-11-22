from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.crud import manager_crud, user_crud, user_role_crud
from app.schemas.user_role_schema import UserRoleCreate
from app.schemas import manager_schema
from app.api import deps
from app.api.auth.auth import has_roles
from app.schemas import stats_schema as schemas
from app.services import stats_service

router = APIRouter()
MANAGER_ONLY = has_roles(["manager"])

@router.post(
    "/",
    response_model=manager_schema.ManagerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGER_ONLY)]
)
def assign_manager(
    manager_in: manager_schema.ManagerCreate,
    db: Session = Depends(deps.get_db)
):
    db_user = user_crud.get_user(db=db, user_id=manager_in.user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {manager_in.user_id} not found."
        )

    existing_manager = manager_crud.get_manager_by_user_id(db=db, user_id=manager_in.user_id)
    if existing_manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id {manager_in.user_id} is already a manager."
        )

    db_manager = manager_crud.create_manager(
        db=db,
        manager_in=manager_in
    )

    existing_role = user_role_crud.get_user_role(db, user_id=manager_in.user_id, role_name="manager")
    if not existing_role:
        user_role_crud.create_user_role(
            db=db,
            role_in=UserRoleCreate(
                user_id=manager_in.user_id,
                role_name="manager",
                assigned_at=datetime.utcnow()
            )
        )

    return db_manager


@router.get(
    "/",
    response_model=List[manager_schema.ManagerRead],
    dependencies=[Depends(MANAGER_ONLY)]
)
def get_all_managers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db)
):
    return manager_crud.get_all_managers(db, skip=skip, limit=limit)

@router.get(
    "/stats",
    response_model=schemas.Stats,
    # Nếu bạn cần bảo vệ endpoint này, bạn có thể thêm dependencies như sau:
    # dependencies=[Depends(deps.get_current_user)] 
)
def get_stats(
    db: Session = Depends(deps.get_db)
):
    """
    Lấy các số liệu thống kê tổng hợp của hệ thống.
    """
    return stats_service.get_stats(db)

@router.get(
    "/{user_id}",
    response_model=manager_schema.ManagerRead,
    dependencies=[Depends(MANAGER_ONLY)]
)
def get_manager(
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    db_manager = manager_crud.get_manager(db, user_id=user_id)
    if not db_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quản lý không tìm thấy."
        )
    return db_manager


@router.put(
    "/{user_id}",
    response_model=manager_schema.ManagerRead,
    dependencies=[Depends(MANAGER_ONLY)]
)
def update_existing_manager(
    user_id: int,
    manager: manager_schema.ManagerUpdate,
    db: Session = Depends(deps.get_db)
):
    db_manager = manager_crud.update_manager(db, user_id=user_id, manager_update=manager)
    if not db_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quản lý không tìm thấy."
        )
    return db_manager


@router.delete(
    "/{user_id}",
    response_model=dict,
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_existing_manager(
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    db_manager = manager_crud.get_manager(db, user_id=user_id)
    if not db_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhân viên không tìm thấy."
        )

    deleted_manager = manager_crud.delete_manager(db, user_id=user_id)

    return {
        "deleted_manager": manager_schema.ManagerRead.from_orm(deleted_manager).dict(),
        "deleted_at": datetime.utcnow().isoformat(),
        "status": "success"
    }
