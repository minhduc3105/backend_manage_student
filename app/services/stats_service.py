from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, select, or_, and_

from app.models.class_model import Class
from app.models.teacher_model import Teacher
from app.models.student_model import Student
from app.models.schedule_model import Schedule, ScheduleTypeEnum, DayOfWeekEnum
from app.schemas.stats_schema import Stats

# Map python weekday (0=Mon, 6=Sun) sang Enum của DB
WEEKDAY_MAP = {
    0: DayOfWeekEnum.MONDAY,
    1: DayOfWeekEnum.TUESDAY,
    2: DayOfWeekEnum.WEDNESDAY,
    3: DayOfWeekEnum.THURSDAY,
    4: DayOfWeekEnum.FRIDAY,
    5: DayOfWeekEnum.SATURDAY,
    6: DayOfWeekEnum.SUNDAY,
}

def get_stats(db: Session) -> Stats:
    """
    Truy vấn thống kê tổng quan (Optimized: 1 DB Round-trip).
    """
    today = date.today()
    
    # 1. Chuẩn bị các Subquery (Chưa thực thi)
    # Dùng select(...).scalar_subquery() để biến câu select thành 1 cột giá trị
    
    sq_classes = select(func.count(Class.class_id)).scalar_subquery()
    sq_teachers = select(func.count(Teacher.user_id)).scalar_subquery()
    sq_students = select(func.count(Student.user_id)).scalar_subquery()

    # 2. Xử lý logic đếm lịch học "HÔM NAY"
    # Logic: (Loại ONCE và trùng ngày) HOẶC (Loại WEEKLY và trùng thứ)
    current_dow = WEEKDAY_MAP.get(today.weekday())
    
    sq_schedules = select(func.count(Schedule.schedule_id)).where(
        or_(
            and_(
                Schedule.schedule_type == ScheduleTypeEnum.ONCE,
                Schedule.date == today
            ),
            and_(
                Schedule.schedule_type == ScheduleTypeEnum.WEEKLY,
                Schedule.day_of_week == current_dow
            )
        )
    ).scalar_subquery()

    # 3. Thực thi 1 lần duy nhất
    # Câu SQL sinh ra sẽ dạng: SELECT (SELECT count...), (SELECT count...), ...
    result = db.execute(
        select(sq_classes, sq_teachers, sq_students, sq_schedules)
    ).first()

    # result là tuple (classes, teachers, students, schedules)
    # Sử dụng `or 0` để an toàn nếu DB trả về None
    return Stats(
        total_classes=result[0] or 0,
        total_teachers=result[1] or 0,
        total_students=result[2] or 0,
        total_schedules=result[3] or 0,
    )