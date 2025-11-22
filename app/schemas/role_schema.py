from pydantic import BaseModel, Field

class RoleBase(BaseModel):
    name: str = Field(..., example="student")

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    role_id: int = Field(..., example=1)

    class Config:
        from_attributes = True