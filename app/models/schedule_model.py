from sqlalchemy import Column, Date, Integer, String, Enum, ForeignKey, Time
from sqlalchemy.orm import relationship
from app.database import Base
import enum

# Định nghĩa Enum cho loại lịch trình
class ScheduleTypeEnum(str, enum.Enum):
    WEEKLY = "WEEKLY"
    ONCE = "ONCE"

# Định nghĩa Enum cho các ngày trong tuần
class DayOfWeekEnum(str, enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"



# Định nghĩa Enum cho loại lịch trình
class ScheduleTypeEnum(str, enum.Enum):
    WEEKLY = "WEEKLY"
    ONCE = "ONCE"

# Định nghĩa Enum cho các ngày trong tuần
class DayOfWeekEnum(str, enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

class Schedule(Base):
    __tablename__ = "schedules"

    schedule_id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=False)
    room = Column(String, nullable=False)
    schedule_type = Column(Enum(ScheduleTypeEnum), nullable=False)
    day_of_week = Column(Enum(DayOfWeekEnum), nullable=False)
    date = Column(Date)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Quan hệ với bảng classes
    class_info = relationship("Class", back_populates="schedules")

    # Quan hệ với attendance
    attendances = relationship("Attendance", back_populates="schedule")