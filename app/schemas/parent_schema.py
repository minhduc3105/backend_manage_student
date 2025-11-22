# app/schemas/parent_schema.py
from datetime import date
from pydantic import BaseModel, field_serializer
from app.models.user_model import GenderEnum

class ParentBase(BaseModel):
    user_id: int

    class Config:
        from_attributes = True


class ParentUpdate(ParentBase):
    pass

class ParentCreate(ParentBase):
    pass

class Child(BaseModel):
    name: str
    email: str
    gender: GenderEnum
    phone_number: str
    date_of_birth: date

    @field_serializer("date_of_birth")
    def format_date_of_birth(self, date_of_birth: date):
        return date_of_birth.strftime("%d/%m/%Y")

    class Config:
        from_attributes = True

