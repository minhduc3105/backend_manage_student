from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.schemas.parent_schema import Child
from app.crud import parent_crud, user_crud, user_role_crud
from app.schemas.user_role_schema import UserRoleCreate
from app.schemas import parent_schema
from app.api import deps
from app.api.auth.auth import get_current_active_user, has_roles
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()
MANAGER_ONLY = has_roles(["manager"])
MANAGER_OR_PARENT = has_roles(["manager", "parent"])

@router.post(
    "/",
    response_model=parent_schema.ParentBase,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGER_ONLY)]
)
def assign_parent(
    parent_in: parent_schema.ParentCreate,
    db: Session = Depends(deps.get_db)
):
    db_user = user_crud.get_user(db=db, user_id=parent_in.user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {parent_in.user_id} not found."
        )

    existing_parent = parent_crud.get_parent_by_user_id(db=db, user_id=parent_in.user_id)
    if existing_parent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id {parent_in.user_id} is already a parent."
        )

    db_parent = parent_crud.create_parent(
        db=db,
        parent_in=parent_schema.ParentCreate(user_id=parent_in.user_id)
    )

    existing_role = user_role_crud.get_user_role(db, user_id=parent_in.user_id, role_name="parent")
    if not existing_role:
        user_role_crud.create_user_role(
            db=db,
            role_in=UserRoleCreate(
                user_id=parent_in.user_id,
                role_name="parent",
                assigned_at=datetime.utcnow()
            )
        )

    return db_parent


@router.get(
    "/",
    response_model=List[parent_schema.ParentBase],
    dependencies=[Depends(MANAGER_ONLY)]
)
def get_all_parents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db)
):
    return parent_crud.get_all_parents(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=parent_schema.ParentBase)
def get_parent(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    db_parent = parent_crud.get_parent(db, user_id=user_id)
    if db_parent is None:
        raise HTTPException(status_code=404, detail="Phụ huynh không tìm thấy.")

    if db_parent.user_id != current_user.user_id and not has_roles(["manager"])(current_user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem thông tin phụ huynh này.")

    return db_parent

@router.get(
    "/{parent_user_id}/children",
    response_model=List[parent_schema.Child],
    summary="Lấy danh sách các con của phụ huynh",
    dependencies=[Depends(MANAGER_OR_PARENT)]
)
def get_parent_children(
    parent_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy danh sách các con của một phụ huynh.
    - Phụ huynh: chỉ được xem danh sách con của mình.
    - Quản lý: có thể xem danh sách con của bất kỳ phụ huynh nào.
    """
    if not ("manager" in current_user.roles) and current_user.user_id != parent_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem danh sách con của phụ huynh khác."
        )

    db_parent = parent_crud.get_parent_by_user_id(db, user_id=parent_user_id)
    if not db_parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phụ huynh có ID {parent_user_id} không tồn tại."
        )

    children = parent_crud.get_children_view(db, parent_user_id=parent_user_id)
    return children

@router.put("/{user_id}", response_model=parent_schema.ParentBase)
def update_existing_parent(
    user_id: int,
    parent_update: parent_schema.ParentUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    db_parent = parent_crud.get_parent(db, user_id=user_id)
    if db_parent is None:
        raise HTTPException(status_code=404, detail="Phụ huynh không tìm thấy.")

    if db_parent.user_id != current_user.user_id and not has_roles(["manager"])(current_user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật thông tin phụ huynh này.")

    return parent_crud.update_parent(db, user_id=user_id, parent_update=parent_update)


@router.delete(
    "/{user_id}",
    response_model=dict,
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_existing_parent(
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    db_parent = parent_crud.get_parent(db, user_id=user_id)
    if db_parent is None:
        raise HTTPException(status_code=404, detail="Phụ huynh không tìm thấy.")

    deleted_parent = parent_crud.delete_parent(db, user_id=user_id)

    return {
        "deleted_parent": parent_schema.ParentBase.from_orm(deleted_parent).dict(),
        "deleted_at": datetime.utcnow().isoformat(),
        "status": "success"
    }
