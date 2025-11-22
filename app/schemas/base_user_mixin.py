from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class BaseUserMixin(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
   
