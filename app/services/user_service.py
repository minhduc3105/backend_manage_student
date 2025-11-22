# app/services/user_service.py
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import delete, select
from app.models import Teacher, Manager, Student, Parent

# Mapping giữa entity string và model + id field
ENTITY_MODEL_MAP = {
    "teacher": (Teacher, Teacher.user_id),
    "manager": (Manager, Manager.user_id),
    "student": (Student, Student.user_id),
    "parent":  (Parent, Parent.user_id),
}

def get_user_id(db: Session, entity: str, entity_id: int) -> Optional[int]:
    """
    Lấy user_id từ entity_id (teacher, manager, student, parent).
    
    Args:
        db (Session): SQLAlchemy session
        entity (str): loại entity ("teacher", "manager", "student", "parent")
        entity_id (int): id của entity
    
    Returns:
        Optional[int]: user_id hoặc None nếu không tìm thấy
    """
    if entity not in ENTITY_MODEL_MAP:
        raise ValueError(f"Entity '{entity}' không hợp lệ. "
                         f"Hãy dùng: {list(ENTITY_MODEL_MAP.keys())}")

    model, id_column = ENTITY_MODEL_MAP[entity]
    stmt = select(model.user_id).where(id_column == entity_id)
    return db.execute(stmt).scalar_one_or_none()


