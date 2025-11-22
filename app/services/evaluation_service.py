from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_, case, join, select, func, literal
from fastapi import HTTPException

from app.models.evaluation_model import Evaluation, EvaluationType
from app.models.class_model import Class
from app.models.subject_model import Subject
from app.models.user_model import User
from app.models.student_model import Student
from app.schemas.evaluation_schema import EvaluationSummary, EvaluationView

# --- Global Aliases (Tạo 1 lần dùng chung để tối ưu bộ nhớ & tốc độ khởi tạo) ---
TeacherUser = aliased(User, name="teacher_user")
StudentUser = aliased(User, name="student_user")
StudentTable = aliased(Student, name="student_table")
ClassTable = aliased(Class, name="classes")
SubjectTable = aliased(Subject, name="subjects")

# --- Helper: permission check ---
def _enforce_student_access_or_raise(
    requesting_user_id: Optional[int], 
    requesting_user_roles: Optional[List[str]], 
    target_student_user_id: int
):
    """
    Chặn student truy cập dữ liệu của student khác.
    """
    if requesting_user_roles and "student" in requesting_user_roles:
        if requesting_user_id is None or requesting_user_id != target_student_user_id:
            raise HTTPException(status_code=403, detail="Học sinh chỉ được xem thông tin của chính mình.")

# --- Main Functions ---

def get_evaluations_by_student_user_id_forCal(
    db: Session, student_user_id: int, skip: int = 0, limit: int = 100
):
    """
    Lấy raw object (dùng cho tính toán nội bộ nếu cần).
    """
    return (
        db.query(Evaluation)
        .filter(Evaluation.student_user_id == student_user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_evaluations_by_student_user_id(
    db: Session, student_user_id: int, skip: int = 0, limit: int = 100,
    requesting_user_id: Optional[int] = None, requesting_user_roles: Optional[List[str]] = None
) -> List[EvaluationView]:
    _enforce_student_access_or_raise(requesting_user_id, requesting_user_roles, student_user_id)

    stmt = (
        select(
            Evaluation.evaluation_id,
            TeacherUser.full_name.label("teacher_name"),
            StudentUser.user_id.label("student_user_id"),
            StudentUser.full_name.label("student_name"),
            ClassTable.class_name,
            SubjectTable.name.label("subject_name"),
            Evaluation.evaluation_type,
            Evaluation.evaluation_date,
            Evaluation.evaluation_content,
        )
        .join(TeacherUser, Evaluation.teacher_user_id == TeacherUser.user_id)
        .join(StudentUser, Evaluation.student_user_id == StudentUser.user_id)
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .where(Evaluation.student_user_id == student_user_id)
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt).all()
    return [
        EvaluationView(
            id=row.evaluation_id,
            teacher=row.teacher_name,
            student_user_id=row.student_user_id,
            student=row.student_name,
            class_name=f"{row.class_name} ({row.subject_name})", 
            type=row.evaluation_type,
            date=row.evaluation_date,
            content=row.evaluation_content,
        )
        for row in result
    ]

def get_all_evaluations_with_names(
    db: Session, skip: int = 0, limit: int = 100,
    requesting_user_id: Optional[int] = None, requesting_user_roles: Optional[List[str]] = None
) -> List[EvaluationView]:
    if requesting_user_roles and "student" in requesting_user_roles:
        raise HTTPException(status_code=403, detail="Học sinh không được phép xem toàn bộ đánh giá.")

    stmt = (
        select(
            Evaluation.evaluation_id,
            TeacherUser.full_name.label("teacher_name"),
            StudentUser.user_id.label("student_user_id"),
            StudentUser.full_name.label("student_name"),
            ClassTable.class_name,
            SubjectTable.name.label("subject_name"),
            Evaluation.evaluation_type,
            Evaluation.evaluation_date,
            Evaluation.evaluation_content,
        )
        .join(TeacherUser, Evaluation.teacher_user_id == TeacherUser.user_id)
        .join(StudentUser, Evaluation.student_user_id == StudentUser.user_id)
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt).all()
    return [
        EvaluationView(
            id=row.evaluation_id,
            teacher=row.teacher_name,
            student_user_id=row.student_user_id,
            student=row.student_name,
            class_name=f"{row.class_name} ({row.subject_name})",
            type=row.evaluation_type,
            date=row.evaluation_date,
            content=row.evaluation_content,
        )
        for row in result
    ]

def get_evaluations_by_teacher_user_id(
    db: Session, teacher_user_id: int, skip: int = 0, limit: int = 100,
    requesting_user_id: Optional[int] = None, requesting_user_roles: Optional[List[str]] = None
) -> List[EvaluationView]:
    if requesting_user_roles and "student" in requesting_user_roles:
        raise HTTPException(status_code=403, detail="Học sinh không được xem danh sách của giáo viên.")

    stmt = (
        select(
            Evaluation.evaluation_id,
            StudentUser.user_id.label("student_user_id"),
            StudentUser.full_name.label("student_name"),
            ClassTable.class_name,
            SubjectTable.name.label("subject_name"),
            Evaluation.evaluation_type,
            Evaluation.evaluation_date,
            Evaluation.evaluation_content,
        )
        .join(StudentUser, Evaluation.student_user_id == StudentUser.user_id)
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .where(Evaluation.teacher_user_id == teacher_user_id)
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt).all()
    return [
        EvaluationView(
            id=row.evaluation_id,
            teacher="", # Context là giáo viên đang xem của chính mình
            student_user_id=row.student_user_id,
            student=row.student_name,
            class_name=f"{row.class_name} ({row.subject_name})",
            type=row.evaluation_type,
            date=row.evaluation_date,
            content=row.evaluation_content,
        )
        for row in result
    ]

def calculate_total_points_for_student(
    db: Session, student_user_id: int,
    requesting_user_id: Optional[int] = None, requesting_user_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    _enforce_student_access_or_raise(requesting_user_id, requesting_user_roles, student_user_id)

    # Sử dụng coalesce để trả về 0 nếu sum là NULL
    stmt = (
        select(
            func.coalesce(func.sum(Evaluation.study_point), 0).label("total_study_point"),
            func.coalesce(func.sum(Evaluation.discipline_point), 0).label("total_discipline_point"),
        )
        .where(Evaluation.student_user_id == student_user_id)
    )
    row = db.execute(stmt).first()
    
    return {
        "student_user_id": student_user_id,
        "final_study_point": row.total_study_point,
        "final_discipline_point": row.total_discipline_point,
    }

def summarize_end_of_semester(db: Session, student_user_id: int) -> Dict[str, Any]:
    total_points = calculate_total_points_for_student(db, student_user_id)
    # Logic min(..., 100)
    return {
        "student_user_id": student_user_id,
        "final_study_point": min(total_points["final_study_point"], 100),
        "final_discipline_point": min(total_points["final_discipline_point"], 100),
    }

def get_evaluations_summary_of_student_in_class(
    db: Session,
    student_user_id: int,
    class_id: int,
    requesting_user_id: Optional[int] = None,
    requesting_user_roles: Optional[List[str]] = None
) -> EvaluationSummary:
    """
    Tối ưu hóa: Sử dụng SQL Aggregation thay vì Python loop.
    Tính tổng điểm và đếm số lần cộng/trừ điểm trực tiếp từ DB.
    """
    _enforce_student_access_or_raise(requesting_user_id, requesting_user_roles, student_user_id)

    stmt = (
        select(
            func.coalesce(func.sum(Evaluation.study_point), 0).label("total_study"),
            func.coalesce(func.sum(Evaluation.discipline_point), 0).label("total_discipline"),
            func.sum(case((Evaluation.study_point > 0, 1), else_=0)).label("study_plus"),
            func.sum(case((Evaluation.study_point < 0, 1), else_=0)).label("study_minus"),
            func.sum(case((Evaluation.discipline_point > 0, 1), else_=0)).label("discipline_plus"),
            func.sum(case((Evaluation.discipline_point < 0, 1), else_=0)).label("discipline_minus"),
            ClassTable.class_name,
            SubjectTable.name.label("subject_name")
        )
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .where(
            and_(
                Evaluation.student_user_id == student_user_id,
                Evaluation.class_id == class_id
            )
        )
        .group_by(ClassTable.class_name, SubjectTable.name)
    )

    row = db.execute(stmt).first()

    # Trường hợp chưa có evaluation nào -> Query riêng tên lớp/môn để trả về object rỗng
    if not row:
        class_info = (
            db.query(Class.class_name, Subject.name)
            .join(Subject, Class.subject_id == Subject.subject_id)
            .filter(Class.class_id == class_id)
            .first()
        )
        
        c_name = class_info.class_name if class_info else ""
        s_name = class_info.name if class_info else ""

        return EvaluationSummary(
            student_user_id=student_user_id,
            class_name=c_name,
            subject=s_name,
            final_study_point=100,       # Mặc định 100
            final_discipline_point=100,  # Mặc định 100
            study_plus_count=0,
            study_minus_count=0,
            discipline_plus_count=0,
            discipline_minus_count=0
        )

    # Tính điểm cuối cùng: Mặc định 100 + delta, max 100
    # Logic cũ: total_study_point = 100 + sum(delta)
    final_s_point = 100 + row.total_study
    final_d_point = 100 + row.total_discipline

    return EvaluationSummary(
        student_user_id=student_user_id,
        class_name=row.class_name,
        subject=row.subject_name,
        final_study_point=min(final_s_point, 100),
        final_discipline_point=min(final_d_point, 100),
        study_plus_count=row.study_plus or 0,
        study_minus_count=row.study_minus or 0,
        discipline_plus_count=row.discipline_plus or 0,
        discipline_minus_count=row.discipline_minus or 0
    )

def get_evaluations_by_student_in_class(
    db: Session,
    student_user_id: int,
    class_id: int,
    skip: int = 0,
    limit: int = 100,
    requesting_user_id: Optional[int] = None,
    requesting_user_roles: Optional[List[str]] = None
) -> List[EvaluationView]:
    _enforce_student_access_or_raise(requesting_user_id, requesting_user_roles, student_user_id)

    stmt = (
        select(
            Evaluation.evaluation_id,
            ClassTable.class_name,
            StudentUser.user_id.label("student_user_id"),
            StudentUser.full_name.label("student_name"),
            TeacherUser.full_name.label("teacher_name"),
            Evaluation.evaluation_type,
            Evaluation.evaluation_content,
            Evaluation.evaluation_date,
            SubjectTable.name.label("subject_name"),
        )
        .join(TeacherUser, Evaluation.teacher_user_id == TeacherUser.user_id)
        .join(StudentUser, Evaluation.student_user_id == StudentUser.user_id)
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .where(
            and_(
                Evaluation.student_user_id == student_user_id,
                Evaluation.class_id == class_id
            )
        )
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    return [
        EvaluationView(
            id=row.evaluation_id,
            class_name=f"{row.class_name} ({row.subject_name})",
            student_user_id=row.student_user_id,
            student=row.student_name,
            teacher=row.teacher_name,
            type=row.evaluation_type,
            content=row.evaluation_content,
            date=row.evaluation_date,
        )
        for row in rows
    ]

def update_late_evaluation(
    db: Session,
    student_user_id: int,
    teacher_user_id: int,
    attendance_date: date,
    new_content: str,
    study_point_penalty: int = 0,
    discipline_point_penalty: int = 0,
    evaluation_type: EvaluationType = EvaluationType.discipline
) -> Evaluation:
    """
    Cập nhật hoặc tạo mới evaluation (Upsert logic).
    """
    evaluation_record = db.query(Evaluation).filter(
        Evaluation.student_user_id == student_user_id,
        Evaluation.teacher_user_id == teacher_user_id,
        Evaluation.evaluation_type == evaluation_type,
        Evaluation.evaluation_date == attendance_date
    ).first()

    if evaluation_record:
        evaluation_record.evaluation_content = new_content
        evaluation_record.study_point = study_point_penalty
        evaluation_record.discipline_point = discipline_point_penalty
    else:
        evaluation_record = Evaluation(
            student_user_id=student_user_id,
            teacher_user_id=teacher_user_id,
            evaluation_date=attendance_date,
            evaluation_content=new_content,
            study_point=study_point_penalty,
            discipline_point=discipline_point_penalty,
            evaluation_type=evaluation_type
        )
        db.add(evaluation_record)

    db.commit()
    db.refresh(evaluation_record)
    return evaluation_record

def get_parent_children_evaluation(
    db: Session, parent_user_id: int, skip: int = 0, limit: int = 100,
    requesting_user_id: Optional[int] = None, requesting_user_roles: Optional[List[str]] = None
) -> List[EvaluationView]:
    """
    Lấy đánh giá của tất cả con thuộc phụ huynh.
    """
    stmt = (
        select(
            Evaluation.evaluation_id,
            TeacherUser.full_name.label("teacher_name"),
            StudentUser.user_id.label("student_user_id"),
            StudentUser.full_name.label("student_name"),
            ClassTable.class_name,
            SubjectTable.name.label("subject_name"),
            Evaluation.evaluation_type,
            Evaluation.evaluation_date,
            Evaluation.evaluation_content,
        )
        .join(StudentTable, Evaluation.student_user_id == StudentTable.user_id) # Join Eval -> Student Table
        .join(StudentUser, StudentTable.user_id == StudentUser.user_id)         # Join Student -> User (lấy tên con)
        .join(TeacherUser, Evaluation.teacher_user_id == TeacherUser.user_id)   # Join Eval -> User (lấy tên GV)
        .join(ClassTable, Evaluation.class_id == ClassTable.class_id)
        .join(SubjectTable, ClassTable.subject_id == SubjectTable.subject_id)
        .where(StudentTable.parent_id == parent_user_id) # Lọc theo parent_id
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt).all()
    return [
        EvaluationView(
            id=row.evaluation_id,
            teacher=row.teacher_name,
            student_user_id=row.student_user_id,
            student=row.student_name,
            class_name=f"{row.class_name} ({row.subject_name})",
            type=row.evaluation_type,
            date=row.evaluation_date,
            content=row.evaluation_content,
        )
        for row in result
    ]