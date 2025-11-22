from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.enrollment_model import Enrollment
from app.models.test_model import Test
from app.models.class_model import Class
from app.schemas.auth_schema import AuthenticatedUser

def validate_student_enrollment(db: Session, student_user_id: int, class_id: int):
    """
    Kiểm tra xem học sinh có đang học trong lớp này không.
    Tối ưu: Chỉ select enrollment_id thay vì toàn bộ object.
    """
    # Chỉ lấy 1 cột (nhẹ hơn lấy cả object)
    exists = db.query(Enrollment.enrollment_id).filter(
        Enrollment.student_user_id == student_user_id,
        Enrollment.class_id == class_id,
        Enrollment.enrollment_status == "active"
    ).first()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {student_user_id} is not actively enrolled in class {class_id}"
        )


def validate_teacher_class(db: Session, current_user: AuthenticatedUser, class_id: int):
    """
    Nếu user là teacher thì chỉ được phép tạo test cho lớp mà mình dạy.
    Tối ưu: Truy vấn trực tiếp teacher_user_id của lớp, không load cả Class object.
    """
    if "teacher" in current_user.roles:
        # Query trả về tuple: (teacher_user_id,) hoặc None
        result = db.query(Class.teacher_user_id).filter(Class.class_id == class_id).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class {class_id} not found"
            )
        
        # result[0] là teacher_user_id thực tế trong DB
        if result[0] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền tạo test cho lớp này"
            )


def validate_unique_test(db: Session, student_user_id: int, test_name: str):
    """
    Không cho phép tạo test trùng (cùng student_user_id + test_name).
    Tối ưu: Chỉ select test_id.
    """
    exists = db.query(Test.test_id).filter(
        Test.student_user_id == student_user_id,
        Test.test_name == test_name
    ).first()

    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {student_user_id} đã có test '{test_name}'"
        )