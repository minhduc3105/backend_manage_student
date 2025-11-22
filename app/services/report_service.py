import logging
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.models.class_model import Class
from app.models.enrollment_model import Enrollment
from app.models.evaluation_model import Evaluation
from app.models.test_model import Test
from app.models.student_model import Student
from app.models.user_model import User
from app.models.attendance_model import Attendance
from app.models.teacher_model import Teacher
from app.models.teacher_review_model import TeacherReview
from app.models.payroll_model import Payroll

from app.schemas.report_schema import TeacherOverview, TeacherReport, SalaryByMonth

# Thiết lập logger
logger = logging.getLogger(__name__)

def get_teacher_overview(db: Session, teacher_user_id: int) -> TeacherOverview:
    """
    Tổng quan giáo viên.
    """
    try:
        # 1. Lấy danh sách Class IDs
        class_ids = [c.class_id for c in db.query(Class.class_id).filter(Class.teacher_user_id == teacher_user_id).all()]
        
        if not class_ids:
            return TeacherOverview(total_students=0, avg_study_point=100, avg_discipline_point=100, avg_gpa=0)

        # 2. Tổng học sinh
        total_students = db.query(func.count(func.distinct(Enrollment.student_user_id))) \
            .filter(Enrollment.class_id.in_(class_ids)) \
            .scalar() or 0

        # 3. Điểm đánh giá trung bình (Cộng thêm 100)
        eval_stats = db.query(
            func.coalesce(func.avg(Evaluation.study_point), 0),
            func.coalesce(func.avg(Evaluation.discipline_point), 0)
        ).filter(Evaluation.class_id.in_(class_ids)).first()
        
        # Logic: Base 100 + Average Delta
        raw_avg_study = float(eval_stats[0]) if eval_stats else 0
        raw_avg_discipline = float(eval_stats[1]) if eval_stats else 0

        avg_study_point = 100 + raw_avg_study
        avg_discipline_point = 100 + raw_avg_discipline

        # 4. GPA Trung bình
        avg_gpa = db.query(func.coalesce(func.avg(Test.score), 0)) \
            .filter(Test.teacher_user_id == teacher_user_id) \
            .scalar()

        return TeacherOverview(
            total_students=total_students,
            avg_study_point=float(round(avg_study_point, 2)),
            avg_discipline_point=float(round(avg_discipline_point, 2)),
            avg_gpa=float(round(avg_gpa, 2)),
        )

    except Exception as e:
        logger.error(f"Error in get_teacher_overview: {e}", exc_info=True)
        # Trả về default 100 điểm nếu lỗi
        return TeacherOverview(total_students=0, avg_study_point=100, avg_discipline_point=100, avg_gpa=0)


def get_class_report(db: Session, class_id: int, teacher_id: int):
    """
    Báo cáo lớp học.
    """
    try:
        # 1. Validate Class
        class_info = db.query(Class).filter(
            Class.class_id == class_id,
            Class.teacher_user_id == teacher_id
        ).first()
        
        if not class_info:
            raise ValueError("Không tìm thấy lớp hoặc không có quyền truy cập.")

        # 2. Lấy danh sách học sinh
        students_query = db.query(User.user_id, User.full_name)\
            .join(Enrollment, Enrollment.student_user_id == User.user_id)\
            .filter(Enrollment.class_id == class_id).all()
        
        if not students_query:
             return {
                "class_id": class_info.class_id, "class_name": class_info.class_name,
                "total_students": 0, "avg_gpa": 0, "avg_study_point": 100,
                "avg_discipline_point": 100, "grade_distribution": {}, "students": []
            }

        student_ids = [s.user_id for s in students_query]
        student_map = {s.user_id: s.full_name for s in students_query}

        # --- BATCH QUERY 1: GPA ---
        gpa_results = db.query(
            Test.student_user_id, 
            func.avg(Test.score).label('avg_score')
        ).filter(
            Test.class_id == class_id,
            Test.student_user_id.in_(student_ids)
        ).group_by(Test.student_user_id).all()
        
        gpa_map = {r.student_user_id: float(r.avg_score) for r in gpa_results}

        # --- BATCH QUERY 2: Evaluation ---
        eval_results = db.query(
            Evaluation.student_user_id,
            func.avg(Evaluation.study_point).label('avg_study'),
            func.avg(Evaluation.discipline_point).label('avg_discipline')
        ).filter(
            Evaluation.class_id == class_id,
            Evaluation.student_user_id.in_(student_ids)
        ).group_by(Evaluation.student_user_id).all()

        # Map delta: {student_id: (delta_study, delta_discipline)}
        eval_map = {r.student_user_id: (float(r.avg_study), float(r.avg_discipline)) for r in eval_results}

        # --- BATCH QUERY 3: Attendance ---
        attendance_results = db.query(
            Attendance.student_user_id,
            func.count(Attendance.attendance_id).label('total'),
            func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present_count')
        ).filter(
            Attendance.class_id == class_id,
            Attendance.student_user_id.in_(student_ids)
        ).group_by(Attendance.student_user_id).all()

        att_map = {}
        for r in attendance_results:
            total = r.total or 0
            present = r.present_count or 0
            att_map[r.student_user_id] = (present / total * 100) if total > 0 else 0

        # --- TỔNG HỢP ---
        students_data = []
        grade_distribution = {i: 0 for i in range(1, 11)}
        
        total_gpa = 0
        total_study = 0
        total_discipline = 0

        for s_id, s_name in student_map.items():
            gpa = gpa_map.get(s_id, 0.0)
            
            # Lấy delta, mặc định 0
            study_delta, discipline_delta = eval_map.get(s_id, (0.0, 0.0))
            
            # TÍNH ĐIỂM CUỐI CÙNG = 100 + Delta
            study_score = 100 + study_delta
            discipline_score = 100 + discipline_delta
            
            attendance = att_map.get(s_id, 0.0)

            # Cộng dồn để tính trung bình lớp
            total_gpa += gpa
            total_study += study_score
            total_discipline += discipline_score

            grade_int = int(round(gpa))
            if 1 <= grade_int <= 10:
                grade_distribution[grade_int] += 1

            students_data.append({
                "id": s_id,
                "name": s_name,
                "gpa": round(gpa, 2),
                "study_point": round(study_score, 2),
                "discipline_point": round(discipline_score, 2),
                "attendance": round(attendance, 1)
            })

        count = len(students_data)
        
        # Trả về kết quả
        return {
            "class_id": class_info.class_id,
            "class_name": class_info.class_name,
            "total_students": count,
            "avg_gpa": round(total_gpa / count, 2) if count else 0,
            "avg_study_point": round(total_study / count, 2) if count else 100,
            "avg_discipline_point": round(total_discipline / count, 2) if count else 100,
            "grade_distribution": grade_distribution,
            "students": students_data
        }

    except Exception as e:
        logger.error(f"Failed to generate class report for class {class_id}: {e}", exc_info=True)
        return None


def get_teacher_report(db: Session, teacher_id: int, year: int) -> TeacherReport:
    """
    Báo cáo cá nhân của giáo viên.
    """
    try:
        # 1. Get Teacher Info
        teacher = db.query(Teacher).filter(Teacher.user_id == teacher_id).first()
        if not teacher:
            raise ValueError("Teacher not found")
        
        teacher_name = getattr(teacher, "teacher_code", str(teacher_id))

        # 2. Review Distribution
        review_counts = db.query(
            func.floor(TeacherReview.rating).label("rating_group"),
            func.count().label("count") 
        ).filter(
            TeacherReview.teacher_user_id == teacher_id
        ).group_by(func.floor(TeacherReview.rating)).all()

        review_distribution = {i: 0 for i in range(1, 6)}
        for r in review_counts:
            star = int(r.rating_group)
            if 1 <= star <= 5:
                review_distribution[star] = r.count

        # 3. Salary by Month
        salary_rows = db.query(
            Payroll.month,
            func.sum(Payroll.total).label("total_salary")
        ).filter(
            Payroll.teacher_user_id == teacher_id,
            func.extract('year', Payroll.sent_at) == year
        ).group_by(Payroll.month).all()

        salary_map = {row.month: float(row.total_salary or 0) for row in salary_rows}

        complete_salary = []
        total_year_salary = 0.0

        for m in range(1, 13):
            amount = salary_map.get(m, 0.0)
            complete_salary.append(SalaryByMonth(month=m, total=amount))
            total_year_salary += amount

        return TeacherReport(
            teacher_id=teacher.user_id,
            teacher_name=teacher_name,
            review_distribution=review_distribution,
            salary_by_month=complete_salary,
            total_year_salary=total_year_salary
        )

    except Exception as e:
        logger.error(f"Error generating teacher report for {teacher_id}: {e}", exc_info=True)
        raise e