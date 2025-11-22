# app/schemas/attendance_schema.py
from pydantic import BaseModel
from datetime import date, time
from typing import List, Optional
from app.models.attendance_model import AttendanceStatus


class AttendanceBase(BaseModel):
    student_user_id: int
    class_id: int
    schedule_id: int
    status: AttendanceStatus
    checkin_time: Optional[time] = None


class AttendanceCreate(AttendanceBase):
    """Schema để tạo bản ghi điểm danh"""
    attendance_date: Optional[date] = None  # cho phép backend tự set hôm nay nếu không truyền



class AttendanceRead(BaseModel):
    """Schema để đọc dữ liệu trả về"""
    attendance_id: int
    student_user_id: int
    schedule_id: int
    class_id: int
    status: AttendanceStatus
    checkin_time: Optional[time] 
    attendance_date: date

    class Config:
        from_attributes = True


# ---- Batch / Special Schemas ----
class AttendanceInitialRecord(BaseModel):
    """Schema mô tả bản ghi điểm danh ban đầu"""
    student_user_id: int
    status: AttendanceStatus
    checkin_time: Optional[time] = None


class AttendanceRecordCreate(BaseModel):
    """Schema để tạo một bản ghi điểm danh kèm ngày"""
    student_user_id: int
    schedule_id: int
    class_id: int
    status: AttendanceStatus
    checkin_time: Optional[time] = None
    attendance_date: date


class AttendanceUpdateLate(BaseModel):
    """Schema update giờ check-in muộn"""
    checkin_time: time
    attendance_date: date


class AttendanceBatchCreate(BaseModel):
    """Schema để tạo nhiều bản ghi điểm danh cho 1 lớp"""
    schedule_id: int
    class_id: int
    attendance_date: date
    records: List[AttendanceInitialRecord]
