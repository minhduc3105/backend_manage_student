from pydantic import BaseModel, ConfigDict
from typing import Optional

class StudentParentAssociationBase(BaseModel):
    """
    Schema cơ sở cho liên kết học sinh và phụ huynh.
    """
    student_user_id: int
    parent_user_id: int

class StudentParentAssociationCreate(StudentParentAssociationBase):
    """Schema để tạo một liên kết học sinh-phụ huynh mới."""
    pass

class StudentParentAssociation(StudentParentAssociationBase):
    """
    Schema đại diện cho một liên kết học sinh-phụ huynh khi được trả về từ API.
    """
    association_id: int
    model_config = ConfigDict(from_attributes=True)
