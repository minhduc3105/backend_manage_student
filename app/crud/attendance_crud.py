from datetime import time
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import insert, and_, select
from sqlalchemy.exc import IntegrityError
from app.models.student_model import Student
from app.models.attendance_model import Attendance, AttendanceStatus
from app.schemas.attendance_schema import AttendanceBatchCreate, AttendanceRecordCreate

def create_initial_attendance_records(db: Session, attendance_data: AttendanceBatchCreate) -> List[Attendance]:
    """
    Tạo bản ghi điểm danh ban đầu cho tất cả học sinh trong một lớp.
    """
    try:
        student_user_ids_to_create = [record.student_user_id for record in attendance_data.records or []]

        # Kiểm tra tồn tại trong Student
        existing_students = db.query(Student).filter(
            Student.user_id.in_(student_user_ids_to_create)
        ).all()
        existing_student_user_ids = {student.user_id for student in existing_students}

        non_existent_ids = [s_id for s_id in student_user_ids_to_create if s_id not in existing_student_user_ids]
        if non_existent_ids:
            raise ValueError(f"Students with user_ids {non_existent_ids} not found.")

        attendance_records = []
        for record in attendance_data.records:
            attendance_records.append({
                "schedule_id": attendance_data.schedule_id,
                "class_id": attendance_data.class_id,
                "attendance_date": attendance_data.attendance_date,
                "status": record.status,  # enum trực tiếp
                "checkin_time": record.checkin_time,
                "student_user_id": record.student_user_id
            })

        stmt = insert(Attendance).values(attendance_records).returning(Attendance)
        result = db.execute(stmt).scalars().all()
        db.commit()
        return result

    except IntegrityError:
        db.rollback()
        raise ValueError("Một hoặc nhiều bản ghi điểm danh đã tồn tại. Không thể tạo bản ghi trùng lặp.")
    except Exception as e:
        db.rollback()
        raise e


def get_attendance_record_by_student_and_date(
    db: Session, student_user_id: int, schedule_id: int, class_id: int, attendance_date: str
) -> Optional[Attendance]:
    """
    Lấy bản ghi điểm danh của một học sinh trong 1 buổi học (schedule + class) vào ngày cụ thể.
    """
    stmt = select(Attendance).where(
        and_(
            Attendance.student_user_id == student_user_id,
            Attendance.schedule_id == schedule_id,
            Attendance.class_id == class_id,
            Attendance.attendance_date == attendance_date
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def update_attendance_status(
    db: Session, db_record: Attendance, new_status: AttendanceStatus, checkin_time: Optional[time] = None
) -> Optional[Attendance]:
    """
    Cập nhật trạng thái và thời gian check-in của một bản ghi điểm danh.
    """
    if db_record:
        db_record.status = new_status
        db_record.checkin_time = checkin_time
        db.commit()
        db.refresh(db_record)
        return db_record
    return None


def update_attendance_record(
    db: Session, student_user_id: int, schedule_id: int, class_id: int, attendance_date: str, update_data: AttendanceRecordCreate
) -> Optional[Attendance]:
    """
    Cập nhật bản ghi điểm danh.
    """
    db_record = get_attendance_record_by_student_and_date(
        db, student_user_id, schedule_id, class_id, attendance_date
    )
    if not db_record:
        return None

    return update_attendance_status(
        db,
        db_record=db_record,
        new_status=update_data.status,
        checkin_time=update_data.checkin_time
    )


def get_absent_attendance_for_student_in_class(
    db: Session, student_user_id: int, schedule_id: int, class_id: int
) -> Optional[Attendance]:
    """
    Tìm bản ghi điểm danh bị đánh dấu là 'absent' của một học sinh trong một lớp cụ thể.
    """
    stmt = select(Attendance).where(
        and_(
            Attendance.student_user_id == student_user_id,
            Attendance.schedule_id == schedule_id,
            Attendance.class_id == class_id,
            Attendance.status == AttendanceStatus.absent
        )
    )
    return db.execute(stmt).scalar_one_or_none()
