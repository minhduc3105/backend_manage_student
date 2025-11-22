# app/schemas/manager_schema.py
from pydantic import BaseModel
from typing import Optional

class ManagerBase(BaseModel):
    user_id: int

    class Config:
        from_attributes = True

class ManagerCreate(ManagerBase):
    pass

class ManagerUpdate(ManagerBase):
    pass

class ManagerRead(ManagerBase):
    pass
