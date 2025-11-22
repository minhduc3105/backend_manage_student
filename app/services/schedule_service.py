# app/services/schedule_service.py
from datetime import date as dt_date, time as dt_time
from typing import List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.crud import schedule_crud, class_crud, parent_crud
from app.models.schedule_model import Schedule, DayOfWeekEnum, ScheduleTypeEnum
from app.schemas.auth_schema import AuthenticatedUser

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------
# Di chuyển map ra ngoài để tránh khởi tạo lại nhiều lần
WEEKDAY_MAP = {
    0: DayOfWeekEnum.MONDAY,
    1: DayOfWeekEnum.TUESDAY,
    2: DayOfWeekEnum.WEDNESDAY,
    3: DayOfWeekEnum.THURSDAY,
    4: DayOfWeekEnum.FRIDAY,
    5: DayOfWeekEnum.SATURDAY,
    6: DayOfWeekEnum.SUNDAY,
}

# ---------------------------------------------------------
# VALIDATION & CONFLICT CHECKS
# ---------------------------------------------------------

def validate_day_of_week_with_date(day_of_week: DayOfWeekEnum, date: Optional[dt_date]):
    """
    Đảm bảo rằng ngày (date) khớp với thứ trong tuần (day_of_week).
    """
    if date is None:
        return
    
    actual_day = WEEKDAY_MAP.get(date.weekday())
    if actual_day != day_of_week:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ngày {date} là {actual_day.value}, không phải {day_of_week.value}."
        )

def check_schedule_conflict(
    db: Session,
    class_id: int,
    day_of_week: DayOfWeekEnum,
    start_time: dt_time,
    end_time: dt_time,
    date: Optional[dt_date] = None,
    room: Optional[str] = None,
    exclude_schedule_id: Optional[int] = None
):
    """
    Kiểm tra xung đột lịch trình trực tiếp trên Database.
    Logic overlap: (StartA < EndB) AND (EndA > StartB)
    """
    # 1. Validate ngày tháng
    validate_day_of_week_with_date(day_of_week, date)

    # 2. Xây dựng query cơ bản: Cùng thứ, thời gian chồng lấn
    # Điều kiện thời gian chồng lấn: Schedule cũ bắt đầu trước khi mới kết thúc VÀ kết thúc sau khi mới bắt đầu
    time_condition = and_(
        Schedule.day_of_week == day_of_week,
        Schedule.start_time < end_time,
        Schedule.end_time > start_time
    )

    if date:
        # Nếu là lịch cụ thể (ONCE), cần check thêm ngày
        # (Hoặc tùy logic của bạn, nếu day_of_week đã khớp thì có thể bỏ qua check date nếu cấu trúc DB lưu cả 2)
        # Ở đây giả định cần check date cho chắc chắn
        time_condition = and_(time_condition, or_(Schedule.date == date, Schedule.date.is_(None)))

    # Base query exclude chính nó (khi update)
    base_query = db.query(Schedule).filter(time_condition)
    
    if exclude_schedule_id:
        base_query = base_query.filter(Schedule.id != exclude_schedule_id)

    # 3. Kiểm tra xung đột LỚP (Class Conflict)
    # Một lớp không thể học 2 môn cùng lúc
    class_conflict = base_query.filter(Schedule.class_id == class_id).first()
    if class_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lịch trình bị chồng chéo với môn học khác của lớp {class_conflict.class_name}." # Giả sử model có relationship class_name hoặc join
        )

    # 4. Kiểm tra xung đột PHÒNG (Room Conflict)
    # Một phòng không thể chứa 2 lớp cùng lúc
    if room:
        room_conflict = base_query.filter(Schedule.room == room).first()
        if room_conflict:
             # Tối ưu: Lấy tên lớp gây xung đột để báo lỗi rõ ràng
            conflict_class_name = getattr(room_conflict, "class_name", f"ID {room_conflict.class_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phòng {room} đã có lịch vào thời gian này với lớp {conflict_class_name}."
            )

# ---------------------------------------------------------
# GETTERS
# ---------------------------------------------------------

def get_schedules_for_teacher(db: Session, teacher_id: int) -> List[Schedule]:
    """
    Lấy danh sách lịch trình dạy của giáo viên.
    Tối ưu: Sử dụng join để query 1 lần thay vì query class rồi mới query schedule.
    """
    # Cách tối ưu: Join Schedule -> Class -> Teacher
    # Giả sử model Schedule có class_id, và Class có teacher_id
    # Nếu chưa cấu hình relationship, ta dùng cách lấy list ID nhưng dùng list comprehension
    
    teacher_classes = class_crud.get_classes_by_teacher_id(db, teacher_id=teacher_id)
    if not teacher_classes:
        return []
    
    class_ids = [cls.class_id for cls in teacher_classes]
    return schedule_crud.get_schedules_by_class_ids(db=db, class_ids=class_ids)


def get_schedules_for_student(db: Session, student_user_id: int) -> List[Schedule]:
    """
    Lấy danh sách lịch học của sinh viên.
    """
    student_class_ids = schedule_crud.get_class_ids_for_student(db, student_user_id=student_user_id)
    if not student_class_ids:
        return []
    
    return schedule_crud.get_schedules_by_class_ids(db=db, class_ids=student_class_ids)

# ---------------------------------------------------------
# SEARCH BY ROLE
# ---------------------------------------------------------

def search_schedules_by_user_role(
    db: Session,
    current_user: AuthenticatedUser,
    class_id: Optional[int] = None,
    schedule_type: Optional[ScheduleTypeEnum] = None,
    day_of_week: Optional[DayOfWeekEnum] = None,
    date: Optional[dt_date] = None,
    room: Optional[str] = None
) -> List[Schedule]:
    """
    Tìm kiếm schedules theo role.
    Tối ưu: Sử dụng Set để loại bỏ trùng lặp class_ids.
    """
    target_class_ids: Optional[List[int]] = None

    # 1. Xác định phạm vi Class IDs dựa trên Role
    if "manager" in current_user.roles:
        # Manager thấy hết -> target_class_ids là None (hoặc list chứa class_id input nếu có)
        if class_id:
            target_class_ids = [class_id]
        else:
            target_class_ids = None # Hàm search của CRUD sẽ hiểu None là lấy tất cả

    elif "teacher" in current_user.roles:
        teacher_classes = class_crud.get_classes_by_teacher_user_id(db, teacher_user_id=current_user.user_id)
        # Dùng Set để unique, sau đó chuyển về list
        valid_ids = {cls.class_id for cls in teacher_classes}
        
        # Nếu user request class_id cụ thể, phải check xem class đó có thuộc quyền giáo viên không
        if class_id:
            if class_id not in valid_ids:
                return [] # Không có quyền xem lớp này
            target_class_ids = [class_id]
        else:
            target_class_ids = list(valid_ids)

    elif "student" in current_user.roles:
        student_class_ids = set(schedule_crud.get_class_ids_for_student(db, student_user_id=current_user.user_id))
        
        if class_id:
            if class_id not in student_class_ids:
                return []
            target_class_ids = [class_id]
        else:
            target_class_ids = list(student_class_ids)

    elif "parent" in current_user.roles:
        childrens = parent_crud.get_childrens(db, parent_user_id=current_user.user_id)
        # Gom tất cả class ID của tất cả con cái vào 1 Set duy nhất
        all_children_class_ids = set()
        for child in childrens:
            # Giả sử hàm này trả về list[int]
            ids = schedule_crud.get_class_ids_for_student(db, student_user_id=child.user_id)
            all_children_class_ids.update(ids)
        
        if class_id:
            if class_id not in all_children_class_ids:
                return []
            target_class_ids = [class_id]
        else:
            target_class_ids = list(all_children_class_ids)
    else:
        # Role không xác định hoặc không có quyền
        return []

    # Nếu target_class_ids là empty list [] nghĩa là role đó không có lớp nào -> return luôn
    if target_class_ids is not None and len(target_class_ids) == 0:
        return []

    # 2. Gọi CRUD để search
    return schedule_crud.search_schedules(
        db=db,
        class_ids=target_class_ids if "manager" not in current_user.roles else None, # Manager pass None để search global, others pass list
        class_id=class_id if "manager" in current_user.roles else None, # Manager filter riêng
        schedule_type=schedule_type,
        day_of_week=day_of_week,
        date=date,
        room=room
    )