from typing import List, Optional, Dict, Tuple
from datetime import datetime, date as dt_date, time as dt_time
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_

# Import Models
from app.models.attendance_model import Attendance, AttendanceStatus
from app.models.evaluation_model import EvaluationType, Evaluation
from app.models.notification_model import Notification, NotificationType
from app.models.schedule_model import Schedule, ScheduleTypeEnum, DayOfWeekEnum
from app.models.class_model import Class
from app.models.student_model import Student, Parent
from app.models.user_model import User 

# Import Schemas
from app.schemas.attendance_schema import AttendanceBatchCreate
from app.schemas.notification_schema import NotificationUpdate
from app.schemas.evaluation_schema import EvaluationCreate

# Import CRUD & Services
from app.crud import (
    attendance_crud,
    notification_crud,
    evaluation_crud,
    schedule_crud,
    student_crud,
    class_crud,
)
from app.services import evaluation_service

# ----------------- Helper để chuẩn hóa time -----------------
def _to_naive_time(t: Optional[dt_time]) -> Optional[dt_time]:
    """
    Chuyển time (hoặc datetime.time/datetime) có tzinfo -> naive (loại bỏ tzinfo).
    Nếu t là None trả về None.
    """
    if t is None:
        return None

    # Nếu client gửi một datetime thay vì time (hiếm), lấy phần time
    if isinstance(t, datetime):
        t = t.time()

    tz = getattr(t, "tzinfo", None)
    if tz is not None:
        try:
            return t.replace(tzinfo=None)
        except Exception:
            return dt_time(t.hour, t.minute, t.second, t.microsecond)
    return t

# ----------------- Check Permission (Optimized) -----------------
def check_attendance_permission(
    db: Session,
    schedule_id: int,
    attendance_date: dt_date,
    checkin_time: Optional[dt_time],
    current_user,
    schedule_obj: Optional[Schedule] = None 
) -> Schedule:
    """
    Kiểm tra quyền điểm danh và khung giờ.
    Tối ưu: Nhận schedule_obj để tránh query lại nếu đã có.
    """
    schedule = schedule_obj
    if not schedule:
        schedule = schedule_crud.get_schedule(db, schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch học.")
    
    # Kiểm tra giáo viên chủ nhiệm lớp
    # Lưu ý: Cần đảm bảo schedule.class_info đã được load (qua joinedload ở hàm gọi) hoặc lazy load
    if schedule.class_info.teacher_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Bạn không được phép điểm danh cho lớp này.")

    # Chuẩn hóa thời gian
    raw_check_time = checkin_time or datetime.now().time()
    time_to_check = _to_naive_time(raw_check_time)
    start_time_naive = _to_naive_time(schedule.start_time)
    end_time_naive = _to_naive_time(schedule.end_time)

    if start_time_naive is None or end_time_naive is None:
        raise HTTPException(status_code=500, detail="Lịch học thiếu thông tin giờ bắt đầu/kết thúc.")

    if start_time_naive <= end_time_naive:
        in_range = (start_time_naive <= time_to_check <= end_time_naive)
    else:
        # Trường hợp qua đêm
        in_range = (time_to_check >= start_time_naive) or (time_to_check <= end_time_naive)

    if not in_range:
        raise HTTPException(
            status_code=403,
            detail=f"Bạn chỉ có thể điểm danh trong giờ học ({schedule.start_time} - {schedule.end_time})."
        )

    return schedule

# ----------------- Create Batch (Optimized) -----------------
def create_batch_attendance(
    db: Session, attendance_data: AttendanceBatchCreate, current_user
) -> List[Attendance]:
    """
    Tạo các bản ghi điểm danh ban đầu cho một lớp.
    Tối ưu: Bulk insert Notification và Evaluation để tránh N+1 query.
    """
    now_time = datetime.now().time()

    # 1. Chuẩn hóa checkin_time trong payload
    representative_checkin = None
    for record in attendance_data.records:
        if record.status == AttendanceStatus.present and record.checkin_time is None:
            record.checkin_time = now_time
        
        if record.checkin_time is not None and representative_checkin is None:
            representative_checkin = _to_naive_time(record.checkin_time)

    # 2. Fetch Schedule kèm Class Info (1 Query)
    schedule = db.query(Schedule).options(joinedload(Schedule.class_info))\
                 .filter(Schedule.schedule_id == attendance_data.schedule_id).first()

    # 3. Check Permission (Tái sử dụng schedule đã fetch)
    check_attendance_permission(
        db=db,
        schedule_id=attendance_data.schedule_id,
        attendance_date=attendance_data.attendance_date,
        checkin_time=representative_checkin,
        current_user=current_user,
        schedule_obj=schedule
    )
    
    class_info = schedule.class_info
    teacher_user_id = class_info.teacher_user_id

    # 4. Tạo Attendance Records (Gọi CRUD)
    try:
        db_records = attendance_crud.create_initial_attendance_records(db, attendance_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 5. Xử lý logic cho sinh viên vắng mặt (Batch Processing)
    absent_records = [r for r in db_records if r.status == AttendanceStatus.absent]
    
    if absent_records:
        absent_student_user_ids = [r.student_user_id for r in absent_records]
        
        # Lấy thông tin Student và User (để lấy tên gửi thông báo)
        # Giả định relationship Student -> User thông qua student_user_id
        students = db.query(Student).options(joinedload(Student.user))\
                     .filter(Student.user_id.in_(absent_student_user_ids)).all()
        
        student_map = {s.user_id: s for s in students}

        # Lấy thông tin Parent (nếu có)
        parents = db.query(Parent).options(joinedload(Parent.user))\
                    .filter(Parent.student_id.in_([s.student_id for s in students])).all()
        
        # Map student_user_id -> Parent Object
        # Lưu ý logic này phụ thuộc vào việc Parent liên kết với Student như thế nào
        # Ở đây giả định Parent có field student_id hoặc quan hệ ngược lại.
        # Để đơn giản và chính xác với logic cũ, ta tạo map: student_id -> parent
        parent_map = {p.student_id: p for p in parents}

        notifications_to_add = []
        evaluations_to_add = []

        for record in absent_records:
            student = student_map.get(record.student_user_id)
            if not student: continue
            
            student_user = student.user # Object User của học sinh

            # 5.1 Notify Student
            notifications_to_add.append(Notification(
                receiver_id=student_user.user_id,
                content=f"Thông báo: Bạn đã vắng mặt trong buổi học ngày {record.attendance_date}.",
                type=NotificationType.warning,
                is_read=False
            ))

            # 5.2 Notify Parent
            parent = parent_map.get(student.student_id)
            if parent and parent.user:
                notifications_to_add.append(Notification(
                    receiver_id=parent.user.user_id,
                    content=f"Thông báo: Con của bạn {student_user.full_name} đã vắng mặt trong buổi học ngày {record.attendance_date}.",
                    type=NotificationType.warning,
                    is_read=False
                ))

            # 5.3 Create Evaluation (Kỷ luật)
            evaluations_to_add.append(Evaluation(
                student_user_id=record.student_user_id,
                teacher_user_id=teacher_user_id,
                class_id=class_info.class_id,
                study_point=-5,
                discipline_point=-5,
                evaluation_content="Vắng mặt không phép trong buổi học.",
                evaluation_type=EvaluationType.discipline,
                created_at=datetime.now()
            ))

        # Bulk Insert
        if notifications_to_add:
            db.add_all(notifications_to_add)
        if evaluations_to_add:
            db.add_all(evaluations_to_add)
        
        db.commit()

    return db_records

# ----------------- Update Late (Optimized) -----------------
def update_late_attendance(
    db: Session,
    student_user_id: int,
    schedule_id: int,
    checkin_time: dt_time,
    attendance_date: dt_date,
    current_user,
) -> Optional[Attendance]:
    """
    Cập nhật trạng thái đi muộn.
    Tối ưu: Sử dụng eager load để giảm query.
    """
    # Fetch record kèm theo tất cả quan hệ cần thiết để xử lý logic sau đó
    attendance_record = (
        db.query(Attendance)
        .options(
            joinedload(Attendance.schedule).joinedload(Schedule.class_info),
            joinedload(Attendance.student).joinedload(Student.user), # Load user info của HS
            joinedload(Attendance.student).joinedload(Student.parent).joinedload(Parent.user) # Load phụ huynh
        )
        .filter(
            Attendance.student_user_id == student_user_id,
            Attendance.schedule_id == schedule_id,
            Attendance.attendance_date == attendance_date,
        )
        .first()
    )

    if not attendance_record or attendance_record.status != AttendanceStatus.absent:
        return None

    # Check permission (dùng lại object đã load)
    check_attendance_permission(
        db=db,
        schedule_id=schedule_id,
        attendance_date=attendance_date,
        checkin_time=checkin_time,
        current_user=current_user,
        schedule_obj=attendance_record.schedule
    )

    # Update Status (Update trực tiếp trên object SQLAlchemy)
    attendance_record.status = AttendanceStatus.late
    attendance_record.checkin_time = checkin_time
    
    # Update Evaluation (Logic nghiệp vụ)
    teacher_user_id = attendance_record.schedule.class_info.teacher_user_id
    evaluation_service.update_late_evaluation(
        db=db,
        student_user_id=student_user_id,
        teacher_user_id=teacher_user_id,
        attendance_date=attendance_date,
        new_content="Đi học muộn",
        study_point_penalty=-2,
        discipline_point_penalty=-2,
    )

    # Update Notifications (Search tối ưu hơn dùng LIKE đơn thuần nếu có thể)
    # Logic: Tìm notif warning chưa đọc của HS/PH có nội dung chứa ngày điểm danh
    student_user = attendance_record.student.user
    parent_obj = attendance_record.student.parent
    parent_user = parent_obj.user if parent_obj else None

    receiver_ids = [student_user.user_id]
    if parent_user:
        receiver_ids.append(parent_user.user_id)
    
    # Tìm notifications liên quan
    notifs = db.query(Notification).filter(
        Notification.receiver_id.in_(receiver_ids),
        Notification.type == NotificationType.warning,
        Notification.is_read == False,
        Notification.content.like(f"%{attendance_record.attendance_date}%") 
    ).all()

    for notif in notifs:
        if notif.receiver_id == student_user.user_id:
            notif.content = f"Thông báo: Bạn đã đi học muộn trong buổi học ngày {attendance_record.attendance_date}."
        elif parent_user and notif.receiver_id == parent_user.user_id:
            notif.content = f"Thông báo: Con của bạn {student_user.full_name} đi học muộn trong buổi học ngày {attendance_record.attendance_date}."
    
    db.commit()
    db.refresh(attendance_record)
    return attendance_record

# ----------------- Get Methods (Restored & Optimized) -----------------
def get_attendances(
    db: Session,
    schedule_id: Optional[int] = None,
    current_user=None
) -> List[Attendance]:
    """
    Lấy danh sách attendance. 
    Tối ưu: Sử dụng joinedload để tránh N+1 khi serializer truy cập relationship.
    """
    query = db.query(Attendance).options(
        joinedload(Attendance.student),
        joinedload(Attendance.schedule).joinedload(Schedule.class_info)
    )

    if schedule_id:
        query = query.filter(Attendance.schedule_id == schedule_id)

    # Nếu user là giáo viên, chỉ cho phép xem điểm danh của lớp mình dạy
    if current_user and "teacher" in current_user.roles:
        # Join với Schedule -> Class để filter theo teacher_user_id
        query = query.join(Attendance.schedule).join(Schedule.class_info)\
                     .filter(Class.teacher_user_id == current_user.user_id)

    return query.all()

def get_all_attendances_no_auth(
    db: Session,
    schedule_id: Optional[int] = None,
) -> List[Attendance]:
    """
    Hàm test không check quyền (dùng cho debug hoặc admin dashboard nếu cần).
    """
    query = db.query(Attendance).options(
        joinedload(Attendance.student),
        joinedload(Attendance.schedule).joinedload(Schedule.class_info)
    )

    if schedule_id is not None:
        query = query.filter(Attendance.schedule_id == schedule_id)

    return query.all()