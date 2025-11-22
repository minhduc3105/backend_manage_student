from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.role_model import Role 
from app.models.manager_model import Manager
from app.schemas.manager_schema import ManagerUpdate, ManagerCreate
from app.models.association_tables import user_roles 

def get_manager(db: Session, user_id: int) -> Optional[Manager]:
    stmt = select(Manager).where(Manager.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()

def get_manager_by_user_id(db: Session, user_id: int) -> Optional[Manager]:
    stmt = select(Manager).where(Manager.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()

def get_all_managers(db: Session, skip: int = 0, limit: int = 100) -> List[Manager]:
    stmt = select(Manager).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()

def create_manager(db: Session, manager_in: ManagerCreate) -> Manager:
    """
    Tạo mới quản lý, chỉ cần user_id. created_at sẽ được set tự động từ model.
    """
    db_manager = Manager(**manager_in.model_dump(exclude_unset=True, exclude={"created_at"}))
    db.add(db_manager)
    db.commit()
    db.refresh(db_manager)
    return db_manager

def update_manager(db: Session, user_id: int, manager_update: ManagerUpdate) -> Optional[Manager]:
    db_manager = get_manager(db, user_id)
    if not db_manager:
        return None
    update_data = manager_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_manager, key, value)
    db.commit()
    db.refresh(db_manager)
    return db_manager

def delete_manager(db: Session, user_id: int):
    db_manager = get_manager(db, user_id=user_id)
    if not db_manager:
        return None

    # Lấy role "manager"
    manager_role = db.query(Role).filter(Role.name == "manager").first()
    if not manager_role:
        return None

    # Xóa chỉ role "manager" cho user này
    db.execute(
        user_roles.delete()
        .where(user_roles.c.user_id == db_manager.user_id)
        .where(user_roles.c.role_id == manager_role.role_id)
    )

    db.delete(db_manager)
    db.commit()
    return db_manager


