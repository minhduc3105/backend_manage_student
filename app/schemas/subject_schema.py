from pydantic import BaseModel, Field
from typing import Optional

class SubjectBase(BaseModel):
    name: str = Field(..., example="Math")

class SubjectCreate(SubjectBase):
    pass

class Subject(SubjectBase):
    subject_id: Optional[int] = None

    class Config:
        from_attributes = True 
        
class SubjectUpdate(SubjectBase):
    pass

    class Config:
        from_attributes = True