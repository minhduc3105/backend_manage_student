# app/crud/user_role_crud.py
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.role_model import Role
from app.schemas.user_role_schema import UserRoleCreate
from app.models.association_tables import user_roles

def create_user_role(db: Session, role_in: UserRoleCreate) -> Optional[dict]:
   
    db_user = db.query(User).filter(User.user_id == role_in.user_id).first()
    db_role = db.query(Role).filter(Role.name == role_in.role_name).first()

    if not db_user or not db_role:
        return None

    if db_role not in db_user.roles:
        try:
            db_user.roles.append(db_role)
            db.commit()
            db.refresh(db_user)
            return {"user_id": db_user.user_id, "role_name": db_role.name}
        except Exception as e:
            db.rollback()
            print(f"Error creating user role: {e}")
            return None

    return {"user_id": db_user.user_id, "role_name": db_role.name} # Tr\u1EA3 v\u1EC1 n\u1EBFu \u0111\u00E3 t\u1ED3n t\u1EA1i

def get_user_role(db: Session, user_id: int, role_name: str) -> Optional[dict]:

    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user:
        for role in db_user.roles:
            if role.name == role_name:
                return {"user_id": db_user.user_id, "role_name": role.name}
    return None

def delete_user_role(db: Session, user_id: int, role_name: str) -> bool:

    db_user = db.query(User).filter(User.user_id == user_id).first()
    db_role = db.query(Role).filter(Role.name == role_name).first()

    if db_user and db_role and db_role in db_user.roles:
        try:
            db_user.roles.remove(db_role)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting user role: {e}")
            return False
    return False

