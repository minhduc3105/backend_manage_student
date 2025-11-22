from pydantic import BaseModel, Field, field_serializer, field_validator
from typing import Optional
from datetime import time, date as dt_date
from app.models.schedule_model import DayOfWeekEnum, ScheduleTypeEnum

# ScheduleBase là schema cơ bản chứa các trường chung
class ScheduleBase(BaseModel):
    class_id: int
    start_time: time
    end_time: time
    
    # Trường để xác định loại lịch
    schedule_type: ScheduleTypeEnum

    # Trường 'room'
    room: Optional[str] = None

    # day_of_week và date là tùy chọn (Optional)
    # Vì một lịch chỉ có thể là tuần lặp lại hoặc đột xuất, không thể là cả hai
    day_of_week: Optional[DayOfWeekEnum] = None
    date: Optional[dt_date] = None


    @field_validator('day_of_week')
    @classmethod
    def validate_weekly_schedule(cls, value, info):
        """
        Validator này đảm bảo day_of_week phải được cung cấp cho lịch WEEKLY.
        """
        if info.data.get('schedule_type') == ScheduleTypeEnum.WEEKLY:
            if value is None:
                raise ValueError('day_of_week must be provided for a WEEKLY schedule')
        return value

    @field_validator('date')
    @classmethod
    def validate_once_schedule(cls, value, info):
        """
        Validator này đảm bảo date phải được cung cấp cho lịch ONCE.
        """
        if info.data.get('schedule_type') == ScheduleTypeEnum.ONCE:
            if value is None:
                raise ValueError('date must be provided for a ONCE schedule')
        return value

# ScheduleCreate để tạo một lịch mới
# Người dùng phải cung cấp schedule_type và một trong hai trường day_of_week hoặc date
class ScheduleCreate(ScheduleBase):
    pass

# ScheduleUpdate để cập nhật một lịch hiện có
# Tất cả các trường đều tùy chọn để có thể cập nhật từng phần
class ScheduleUpdate(ScheduleBase):
    pass

# Schedule là schema đại diện cho dữ liệu đã được lưu
class Schedule(ScheduleBase):
    schedule_id: int

    class Config:
        from_attributes = True


class ScheduleView(BaseModel):
    id: int
    class_name: str 
    room: Optional[str] 
    schedule_type: ScheduleTypeEnum
    day_of_week: Optional[DayOfWeekEnum] 
    date: Optional[dt_date] 
    start_time: time 
    end_time: time 
    subject: str
    students: Optional[int] = Field(None, description="Số lượng học sinh trong lớp")
    class_id: int

    @field_serializer('date')
    def serialize_date(self, value: Optional[dt_date], info):
        if value is None:
            return None
        # Chuyển đổi đối tượng date thành chuỗi 'dd/mm/yyyy'
        return value.strftime('%d/%m/%Y')

    class Config:
        from_attributes = True