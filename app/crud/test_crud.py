from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from typing import List

# ✅ Dùng SQLAlchemy model cho thao tác DB
from app.models.test_model import Test
from app.models.class_model import Class
from app.models.student_model import Student
from app.models.user_model import User

# ✅ Dùng Pydantic schema cho dữ liệu vào/ra
from app.schemas.test_schema import TestBase, TestCreate, TestUpdate
from app.schemas.auth_schema import AuthenticatedUser

from app.services.test_service import validate_student_enrollment


def create_test(db: Session, test_in: TestCreate, current_user: AuthenticatedUser):
    db_class = db.get(Class, test_in.class_id)
    if not db_class:
        return None

    # Validate enrollment
    validate_student_enrollment(db, test_in.student_user_id, test_in.class_id)

    # Nếu user là teacher -> chỉ được tạo test cho lớp của mình
    if "teacher" in current_user.roles and db_class.teacher_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Teacher {current_user.user_id} không có quyền tạo test cho class {test_in.class_id}"
        )

    # Check trùng test (student_id + test_name)
    duplicate = db.query(Test).filter(
        Test.student_user_id == test_in.student_user_id,
        Test.test_name == test_in.test_name
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {test_in.student_user_id} đã có test {test_in.test_name}"
        )

    db_test = Test(
        test_name=test_in.test_name,
        student_user_id=test_in.student_user_id,
        class_id=test_in.class_id,
        teacher_user_id=db_class.teacher_user_id,
        score=test_in.score,
        exam_date=test_in.exam_date,
        test_type=test_in.test_type
    )
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test


def update_test(db: Session, test_id: int, test_update: TestUpdate, current_user):
    # 1. Tìm bài kiểm tra
    db_test = db.query(Test).filter(Test.test_id == test_id).first()
    if not db_test:
        return None

    # 2. Kiểm tra quyền của Teacher (Logic này giữ nguyên)
    # Lấy class_id của bài test hiện tại để kiểm tra quyền
    if "teacher" in current_user.roles:
        db_class = db.get(Class, db_test.class_id)
        if not db_class or db_class.teacher_user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền cập nhật bài kiểm tra này."
            )

    # 3. Loại bỏ student_user_id và class_id khỏi dữ liệu cập nhật
    # Danh sách các trường KHÔNG được phép cập nhật
    EXCLUDE_FIELDS = {"student_user_id", "class_id", "teacher_user_id"} 
    
    update_data = test_update.model_dump(exclude_unset=True)

    # Loại bỏ các trường không cho phép cập nhật
    update_data_filtered = {
        key: value 
        for key, value in update_data.items() 
        if key not in EXCLUDE_FIELDS
    }
    
    # 4. Áp dụng cập nhật (chỉ cho các trường còn lại)
    # KHÔNG CẦN VALIDATE ENROLLMENT VÀ LOGIC UPDATE TEACHER NỮA

    for key, value in update_data_filtered.items():
        setattr(db_test, key, value)

    # 5. Commit và trả về
    db.commit()
    db.refresh(db_test)
    return db_test


def get_test(db: Session, test_id: int, current_user: AuthenticatedUser = None):
    stmt = select(Test).where(Test.test_id == test_id)
    test = db.execute(stmt).scalars().first()

    if not test:
        return None

    # Nếu user là teacher -> chỉ cho phép xem test của lớp mình dạy
    if current_user and "teacher" in current_user.roles:
        db_class = db.get(Class, test.class_id)
        if not db_class or db_class.teacher_user_id != current_user.user_id:
            return None

    if current_user and "student" in current_user.roles:
        db_student = db.get(Student, test.student_user_id)
        if not db_student or db_student.user_id != current_user.user_id:
            return None

    return test


def delete_test(db: Session, test_id: int, current_user: AuthenticatedUser):
    db_test = db.query(Test).filter(Test.test_id == test_id).first()
    if not db_test:
        return None

    # Nếu teacher thì chỉ xóa test của lớp mình
    if "teacher" in current_user.roles:
        db_class = db.get(Class, db_test.class_id)
        if not db_class or db_class.teacher_user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa bài kiểm tra này."
            )

    db.delete(db_test)
    db.commit()
    return db_test


def get_tests_by_student_user_id(db: Session, student_user_id: int, skip: int = 0, limit: int = 100):
    """Lấy danh sách các bài kiểm tra theo student_user_id."""
    stmt = select(Test).where(Test.student_user_id == student_user_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_tests_by_teacher_user_id(db: Session, teacher_user_id: int, skip: int = 0, limit: int = 100):
    """Lấy danh sách các bài kiểm tra theo teacher_user_id."""
    stmt = select(Test).where(Test.teacher_user_id == teacher_user_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


from sqlalchemy import select, or_
from sqlalchemy.orm import Session
# Giả định các import cần thiết khác như Test, Class, Student, User, AuthenticatedUser
# VÀ TestBase (Pydantic model)

def get_all_tests(db: Session, current_user: AuthenticatedUser, skip: int = 0, limit: int = 100):
    
    # BƯỚC 1: Xây dựng truy vấn cơ sở với LEFT JOIN
    stmt = (
        select(
            Test.test_id,
            Test.test_name,
            Test.student_user_id,
            User.full_name.label("student_name"),
            Test.class_id,
            Class.class_name,
            Test.teacher_user_id,
            Test.score,
            Test.exam_date,
            Test.test_type
        )
        # LEFT JOIN thay vì JOIN để Manager vẫn lấy test kể cả khi User/Class không tồn tại
        .outerjoin(Class, Test.class_id == Class.class_id)
        .outerjoin(User, Test.student_user_id == User.user_id)
    )

    # BƯỚC 2: Xử lý filter theo vai trò
    
    filters = []


    if "teacher" in current_user.roles:
        filters.append(Test.teacher_user_id == current_user.user_id)

    if "student" in current_user.roles:
        filters.append(Test.student_user_id == current_user.user_id)

    if "parent" in current_user.roles and "manager" not in current_user.roles:
        child_students = db.execute(
            select(Student.user_id).where(Student.parent_id == current_user.user_id)
        ).scalars().all()
        if child_students:
            filters.append(Test.student_user_id.in_(child_students))
        else:
            filters.append(Test.test_id == -1)

    # Chỉ áp dụng filter nếu filters không rỗng
    if filters:
        stmt = stmt.where(or_(*filters))
    # Manager: filters rỗng => lấy tất cả test

    # BƯỚC 3: Phân trang
    stmt = stmt.offset(skip).limit(limit)

    results = db.execute(stmt).all()

    # BƯỚC 4: Map tuple -> Pydantic
    return [TestBase.model_validate(row._asdict()) for row in results]
