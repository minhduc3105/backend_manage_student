from sqlalchemy.orm import Session
from sqlalchemy import func, select, join
from typing import Optional, List
from datetime import date as dt_date, time
from app.schemas import schedule_schema
from app.models.schedule_model import Schedule, DayOfWeekEnum, ScheduleTypeEnum
from app.models.class_model import Class
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate, ScheduleView
from app.models.enrollment_model import Enrollment
from app.services import schedule_service
from app.services.service_helper import to_naive_time
from app.models.subject_model import Subject


# Helper function để lấy truy vấn JOIN giữa Schedule và Class
def get_schedule_with_class_name_query():
    """Returns a SQLAlchemy query object with JOINs to get class name, subject name, and student count."""
    return (
        select(
            Schedule.schedule_id.label("id"),
            Class.class_name,
            Schedule.room,
            Schedule.schedule_type,
            Schedule.day_of_week,
            Schedule.date,
            Schedule.start_time,
            Schedule.end_time,
            Subject.name.label("subject"),
            func.count(Enrollment.student_user_id).label("students"),  
            Schedule.class_id
        )
        .select_from(
            join(
                join(
                    Schedule,
                    Class,
                    Schedule.class_id == Class.class_id,
                ),
                Subject,
                Class.subject_id == Subject.subject_id,
                isouter=True,
            )
            .join(
                Enrollment,
                Enrollment.class_id == Class.class_id,
                isouter=True,  
            )
        )
        .group_by(
            Schedule.schedule_id,
            Class.class_name,
            Schedule.room,
            Schedule.schedule_type,
            Schedule.day_of_week,
            Schedule.date,
            Schedule.start_time,
            Schedule.end_time,
            Subject.name,
        )
    )


def get_schedule_by_id(db: Session, schedule_id: int) -> Optional[ScheduleView]:
    """
    Lấy một lịch trình cụ thể dựa trên schedule_id, trả về ScheduleView object.
    """
    query = get_schedule_with_class_name_query().where(Schedule.schedule_id == schedule_id)
    result = db.execute(query).first()
    if result:
        return ScheduleView.model_validate(result._asdict())
    return None

def create_schedule(db: Session, schedule_in: ScheduleCreate, current_user):
    if not any(role in ["manager", "teacher"] for role in current_user.roles):
        raise PermissionError("Bạn không có quyền tạo lịch.")

    schedule_service.check_schedule_conflict(
        db=db,
        class_id=schedule_in.class_id,
        day_of_week=schedule_in.day_of_week,
        start_time=schedule_in.start_time,
        end_time=schedule_in.end_time,
        date=schedule_in.date,
        room=schedule_in.room,
        exclude_schedule_id=None
    )

    db_schedule = Schedule(**schedule_in.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

def update_schedule(db: Session, schedule: Schedule, schedule_in: ScheduleUpdate) -> Schedule:
    update_data = schedule_in.model_dump(exclude_unset=True)

    # Convert sang naive time trước khi check conflict
    class_id = update_data.get("class_id", schedule_in.class_id)
    day_of_week = update_data.get("day_of_week", schedule_in.day_of_week)
    start_time = to_naive_time(update_data.get("start_time", schedule.start_time))
    end_time = to_naive_time(update_data.get("end_time", schedule.end_time))
    date = update_data.get("date", schedule.date)
    room = update_data.get("room", schedule.room)
    schedule_type = update_data.get("schedule_type", schedule.schedule_type)

    if schedule_type == "WEEKLY":
        date = None

    schedule_service.check_schedule_conflict(
        db=db,
        class_id=class_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        date=date,
        room=room,
        exclude_schedule_id=schedule.schedule_id
    )

    # Cập nhật các field còn lại
    for field, value in update_data.items():
        if field in ["start_time", "end_time"]:
            setattr(schedule, field, to_naive_time(value))
        else:
            setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: Schedule):
    """
    Xóa một lịch trình.
    """
    db.delete(schedule)
    db.commit()

def search_schedules(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    class_id: Optional[int] = None,
    class_ids: Optional[List[int]] = None,
    day_of_week: Optional[DayOfWeekEnum] = None,
    schedule_type: Optional[ScheduleTypeEnum] = None,
    date: Optional[dt_date] = None,
    room: Optional[str] = None
) -> List[ScheduleView]:
    """
    Tìm kiếm và lọc các lịch trình dựa trên nhiều tiêu chí, trả về ScheduleView object.
    Hàm này đã được bổ sung tham số skip và limit để hỗ trợ phân trang.
    """
    query = get_schedule_with_class_name_query()

    if class_id is not None:
        query = query.where(Schedule.class_id == class_id)
    if class_ids:
        query = query.where(Schedule.class_id.in_(class_ids))
    if day_of_week is not None:
        query = query.where(Schedule.day_of_week == day_of_week)
    if schedule_type is not None:
        query = query.where(Schedule.schedule_type == schedule_type)
    if date is not None:
        query = query.where(Schedule.date == date)
    if room is not None:
        query = query.where(Schedule.room == room)

    results = db.execute(query.offset(skip).limit(limit)).all()
    return [ScheduleView.model_validate(row._asdict()) for row in results]
    
    
def get_classes_for_teacher(db: Session, teacher_user_id: int) -> List[Class]:
    """
    Lấy danh sách các lớp học của một giáo viên cụ thể.
    """
    return db.query(Class).filter(Class.teacher_user_id == teacher_user_id).all()

def get_class_ids_for_student(db: Session, student_user_id: int) -> List[int]:
    """
    Lấy danh sách class_id mà sinh viên đang học (chỉ enrollment_status = 'active').
    """
    stmt = select(Enrollment.class_id).where(
        Enrollment.student_user_id == student_user_id,
        Enrollment.enrollment_status == "active"
    )
    return db.execute(stmt).scalars().all()


def get_schedules_by_class_ids(db: Session, class_ids: List[int]) -> List[ScheduleView]:
    """
    Lấy tất cả các lịch trình thuộc danh sách class_id, trả về ScheduleView object.
    """
    query = get_schedule_with_class_name_query().where(Schedule.class_id.in_(class_ids))
    results = db.execute(query).all()
    return [ScheduleView.model_validate(row._asdict()) for row in results]

def get_classes_by_teacher_user_id(db: Session, teacher_user_id: int) -> List[Class]:
    """
    Lấy danh sách các lớp học của một giáo viên cụ thể.
    Đồng bộ tên hàm với service.
    """
    return db.query(Class).filter(Class.teacher_user_id == teacher_user_id).all()

def get_schedule(db: Session, schedule_id: int) -> Schedule | None:
    """
    Lấy một lịch học theo schedule_id.
    Trả về Schedule object hoặc None nếu không tìm thấy.
    """
    return db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()

