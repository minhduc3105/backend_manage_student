from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, select, delete
from app.models.student_model import Student
from app.schemas.student_schema import StudentUpdate, StudentCreate, StudentView
from app.models.parent_model import Parent
from app.models.user_model import User
from app.models.role_model import Role
from app.models.association_tables import user_roles
from app.models.test_model import Test
from app.schemas.stats_schema import StudentStats
from app.services.evaluation_service import summarize_end_of_semester
from app.models.enrollment_model import Enrollment
from app.schemas.class_schema import ClassView
from app.models.class_model import Class
from app.models.subject_model import Subject
from app.schemas.teacher_schema import TeacherView
from app.crud import teacher_crud

def get_student(db: Session, student_user_id: int) -> Optional[StudentView]:
    """
    Lấy thông tin sinh viên bằng cách JOIN bảng Student và User, 
    trả về dưới dạng StudentView.
    """
    stmt = (
        select(
            # Chọn các trường từ Student
            Student.user_id.label("student_user_id"),
            # Chọn các trường cần thiết từ User
            User.full_name,
            User.email,
            User.date_of_birth,
            User.phone_number,
            User.gender,
        )
        .join(User, Student.user_id == User.user_id)
        .where(Student.user_id == student_user_id)
    )

    result = db.execute(stmt).one_or_none()

    if result:
        return StudentView.model_validate(result._asdict())

    return None


def get_student_with_user(db: Session, user_id: int) -> Optional[Tuple[Student, User]]:
    """
    Lấy học sinh và user liên kết theo user_id.
    """
    result = db.execute(
        select(Student, User)
        .join(User, Student.user_id == User.user_id)
        .where(Student.user_id == user_id)
    ).first()
    return result if result else (None, None)


def get_parent_by_user_id(db: Session, user_id: int) -> Optional[Tuple[Parent, User]]:
    """
    Lấy phụ huynh duy nhất (1-n) của học sinh.
    """
    return db.execute(
        select(Parent, User)
        .join(User, Parent.user_id == User.user_id)
        .join(Student, Student.parent_id == Parent.user_id)
        .where(Student.user_id == user_id)
    ).first()


def get_student_by_user_id(db: Session, user_id: int) -> Optional[Student]:
    return db.execute(
        select(Student).where(Student.user_id == user_id)
    ).scalar_one_or_none()


def get_students_by_class_id(db: Session, class_id: int, skip: int = 0, limit: int = 100) -> List[Student]:
    """
    Lấy danh sách học sinh trong 1 lớp.
    Vì Student–Class là many-to-many nên cần join qua relationship.
    """
    return db.execute(
        select(Student)
        .join(Student.classes)   # join qua relationship
        .where(Student.classes.any(class_id=class_id))
        .offset(skip)
        .limit(limit)
    ).scalars().all()


def get_students_for_role(
    db: Session, 
    teacher_user_id: Optional[int] = None, 
    skip: int = 0, 
    limit: int = 100
) -> List[StudentView]:
    """
    Lấy danh sách học sinh. 
    - Nếu teacher_user_id là None (Manager): Lấy tất cả học sinh.
    - Nếu teacher_user_id có giá trị (Teacher): Chỉ lấy học sinh thuộc các lớp mà giáo viên đó dạy.
    
    Kết quả được join với bảng User để trả về StudentView.
    """
    
    # Bắt đầu truy vấn: Chọn các trường cần thiết cho StudentView
    stmt = select(
        Student.user_id.label("student_user_id"),
        User.full_name,
        User.email,
        User.date_of_birth,
        User.phone_number,
        User.gender,
        Class.class_name.label("class_name") # Lấy tên lớp gần nhất hoặc chỉ lấy 1 tên lớp bất kỳ
    ).join(User, Student.user_id == User.user_id) # Join User để lấy thông tin cá nhân
    
    # Lọc cho Giáo viên
    if teacher_user_id is not None:
        # Join qua Enrollment và Class để lọc những học sinh thuộc lớp của giáo viên
        stmt = stmt.join(Enrollment, Enrollment.student_user_id == Student.user_id)
        stmt = stmt.join(Class, Class.class_id == Enrollment.class_id)
        # Thêm điều kiện: teacher_user_id của Class phải là ID của giáo viên hiện tại
        stmt = stmt.where(Class.teacher_user_id == teacher_user_id)
    else:
        # Nếu là Manager, vẫn cần join Class để lấy class_name (dù là bất kỳ lớp nào)
        # Sử dụng outerjoin để đảm bảo học sinh không có lớp vẫn được hiển thị
        stmt = stmt.outerjoin(Enrollment, Enrollment.student_user_id == Student.user_id)
        stmt = stmt.outerjoin(Class, Class.class_id == Enrollment.class_id)
        
    # Nhóm theo học sinh để tránh trùng lặp nếu học sinh ở nhiều lớp
    # Lấy class_name đầu tiên (sẽ phức tạp nếu muốn lớp gần nhất)
    stmt = stmt.group_by(
        Student.user_id, User.full_name, User.email, User.date_of_birth, User.phone_number, User.gender, Class.class_name
    )

    # Thêm phân trang
    stmt = stmt.offset(skip).limit(limit)
    
    results = db.execute(stmt).all()

    # Chuyển đổi kết quả thành List[StudentView]
    student_views = []
    for row in results:
        student_views.append(StudentView.model_validate(row, from_attributes=True))
        
    return student_views


def create_student(db: Session, student_in: StudentCreate) -> Student:
    db_student = Student(**student_in.model_dump(exclude_unset=True, exclude={"created_at"}))
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def update_student(db: Session, user_id: int, student_update: StudentUpdate) -> Optional[Student]:
    db_student = get_student(db, user_id)
    if db_student:
        update_data = student_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_student, key, value)
        db.commit()
        db.refresh(db_student)
    return db_student


def delete_student(db: Session, user_id: int):
    db_student = get_student(db, user_id=user_id)
    if not db_student:
        return None

    # Lấy role "student"
    student_role = db.query(Role).filter(Role.name == "student").first()
    if not student_role:
        return None

    # Xóa chỉ role "student" cho user này (không ảnh hưởng role khác)
    db.execute(
        user_roles.delete()
        .where(user_roles.c.user_id == db_student.user_id)
        .where(user_roles.c.role_id == student_role.role_id)
    )

    db.delete(db_student)
    db.commit()
    return db_student


def calculate_gpa(db: Session, student_user_id: int) -> Optional[float]:
    """
    Tính điểm trung bình học tập (GPA) từ tất cả các bản ghi Test của học sinh.
    GIẢ ĐỊNH: Model Test có trường 'score' (float) và liên kết với student_user_id.
    """
    # Lấy điểm trung bình của tất cả các bài kiểm tra (Test)
    avg_score = db.execute(
        select(func.avg(Test.score))
        .where(Test.student_user_id == student_user_id)
    ).scalar_one_or_none()
    
    return avg_score


def get_classes_enrolled_count(db: Session, student_user_id: int) -> int:
    student = get_student(db, student_user_id)
    if not student:
        return 0
    
    enrollment_count = db.execute(
        select(func.count(Enrollment.class_id))
        .where(Enrollment.student_user_id == student_user_id)
        .where(Enrollment.enrollment_status == "active")
    ).scalar_one_or_none()
    
    return enrollment_count if enrollment_count is not None else 0

# Bỏ async vì không còn gọi API bất đồng bộ
def get_student_stats(db: Session, student_user_id: int) -> StudentStats:
    """
    Tổng hợp các chỉ số thống kê của học sinh.
    """
    # 1. Tính GPA
    gpa_result = calculate_gpa(db, student_user_id)

    # 2. Đếm số lớp đã đăng ký
    classes_count = get_classes_enrolled_count(db, student_user_id)

    # 3. Lấy điểm học tập và kỷ luật bằng cách gọi hàm trực tiếp
    evaluation_summary = summarize_end_of_semester(db, student_user_id)
    
    study_point = None
    discipline_point = None
    
    if evaluation_summary:
        # Lấy giá trị số nguyên từ kết quả trả về
        study_point = 100 + evaluation_summary.get("final_study_point")
        discipline_point = 100 + evaluation_summary.get("final_discipline_point")

    return StudentStats(
        classes_enrolled=classes_count,
        # Làm tròn GPA để dễ hiển thị
        gpa=round(gpa_result, 2) if gpa_result is not None else None,
        study_point=study_point,
        discipline_point=discipline_point,
    )

def get_student_active_classes(db: Session, student_user_id: int) -> List[ClassView]:
    """
    Lấy danh sách các lớp học mà học sinh đang tham gia với trạng thái 'active'.
    Dữ liệu được trả về dưới dạng ClassView.
    """
    # Query để chọn các trường cần thiết cho ClassView
    # Lấy thông tin lớp học (Class), tên giáo viên (User) và tên môn học (Subject)
    stmt = (
        select(
            # Class fields
            Class.teacher_user_id,
            Class.class_id,
            Class.class_name,
            Class.capacity,
            Class.fee,
            # Joined fields
            User.full_name.label("teacher_name"), # Giáo viên
            Subject.name.label("subject_name")    # Môn học
        )
        .join(Enrollment, Enrollment.class_id == Class.class_id) # 1. Join Enrollment
        .join(User, Class.teacher_user_id == User.user_id)       # 2. Join User (Giáo viên)
        .join(Subject, Class.subject_id == Subject.subject_id)   # 3. Join Subject
        .where(Enrollment.student_user_id == student_user_id)    # 4. Lọc theo ID học sinh
        .where(Enrollment.enrollment_status == "active")         # 5. Lọc trạng thái active
    )
    
    result = db.execute(stmt).all()
    
    classes_list = []
    # Chuyển đổi kết quả truy vấn thành danh sách các đối tượng ClassView
    for row in result:
        # Sử dụng row._asdict() hoặc lấy từng trường và gán vào ClassView
        # Giả định ClassView là Pydantic model có thể nhận kwargs
        classes_list.append(
            ClassView(
                teacher_user_id=row.teacher_user_id,
                class_id=row.class_id,
                class_name=row.class_name,
                teacher_name=row.teacher_name,
                subject_name=row.subject_name,
                capacity=row.capacity,
                fee=row.fee
            )
        )
        
    return classes_list

def get_student_teachers(db: Session, student_user_id: int) -> List[TeacherView]:
    """
    Trả về danh sách các giáo viên của một học sinh, bao gồm thông tin user 
    và danh sách các lớp học mà giáo viên đó đang dạy.
    """
    # 1. Truy vấn để lấy thông tin giáo viên (User) liên quan đến học sinh qua Enrollment
    stmt = (
        select(
            User.user_id.label("teacher_user_id"), 
            User.full_name, 
            User.email, 
            User.date_of_birth
        )
        .join(Class, Class.teacher_user_id == User.user_id) 
        .join(Enrollment, Enrollment.class_id == Class.class_id) 
        
        .where(Enrollment.student_user_id == student_user_id)
        .distinct()
    )

    teacher_results = db.execute(stmt).all()
    
    teacher_views: List[TeacherView] = []
    
    # 2. Lặp qua từng giáo viên và lấy danh sách các lớp họ dạy
    for row in teacher_results:
        teacher_user_id = row.teacher_user_id
        
        # Gọi hàm service khác để lấy danh sách các lớp giáo viên đó dạy
        classes_taught_models: List[Class] = teacher_crud.get_classes_taught_by_teacher(db, teacher_user_id)
        
        # Chuyển đổi danh sách Class model thành list[str] (chỉ lấy class_name)
        class_names: List[str] = [class_model.class_name for class_model in classes_taught_models]
        
        # Tạo đối tượng TeacherView
        teacher_views.append(
            TeacherView(
                teacher_user_id=teacher_user_id,
                full_name=row.full_name,
                email=row.email,
                date_of_birth=row.date_of_birth,
                class_taught=class_names
            )
        )
        
    return teacher_views