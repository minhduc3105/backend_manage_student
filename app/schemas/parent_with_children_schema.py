from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from .parent_schema import ParentCreate
from .student_schema import StudentCreate

class ParentWithChildrenCreate(BaseModel):
    """
    Schema để đăng ký một Parent cùng với một hoặc nhiều Student.
    """
    # Sử dụng `Field` với `example` để tạo tài liệu API tốt hơn
    parent_info: ParentCreate = Field(..., description="Thông tin chi tiết của phụ huynh")
    
    # Sử dụng `Field` với `min_length` để đảm bảo danh sách không rỗng
    children_info: List[StudentCreate] = Field(
        ...,
        min_length=1,
        description="Danh sách thông tin của các học sinh là con của phụ huynh này"
    )

    # `model_config` là cách hiện đại để cấu hình Pydantic, việc này rất tốt
    model_config = ConfigDict(from_attributes=True)
