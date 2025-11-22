from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List

# Import các CRUD operations và schemas đã được cập nhật
from app.crud import test_crud
from app.crud import student_crud
from app.crud import class_crud
from app.schemas import test_schema
from app.api import deps
# Import dependency factory
from app.api.auth.auth import has_roles, get_current_active_user
from app.services.excel_services.import_tests import import_tests_from_excel

router = APIRouter()

# Khai báo Dependency: MANAGER_ONLY và MANAGER_OR_TEACHER đã là đối tượng Depends
# Không cần bọc thêm Depends() khi sử dụng chúng trong dependencies=[...]
# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = Depends(has_roles(["manager"]))

# Dependency cho quyền truy cập của Manager hoặc Teacher
MANAGER_OR_TEACHER = Depends(has_roles(["manager", "teacher"]))

@router.post(
    "/",
    response_model=test_schema.Test,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một bài kiểm tra mới",
    dependencies=[MANAGER_OR_TEACHER]
)
def create_new_test(
    test_in: test_schema.TestCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user)
):

    db_student = student_crud.get_student(db, student_user_id=test_in.student_user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail=f"Student with id {test_in.student_user_id} not found.")

    db_class = class_crud.get_class(db, class_id=test_in.class_id)
    if not db_class:
        raise HTTPException(status_code=404, detail=f"Class with id {test_in.class_id} not found.")

    # Tạo test có validate quyền teacher
    db_test = test_crud.create_test(db, test_in, current_user)
    if not db_test:
        raise HTTPException(status_code=400, detail="Không thể tạo bài kiểm tra.")

    return db_test

# --- ENDPOINT: Lấy tất cả bài kiểm tra (áp dụng phân quyền) ---
@router.get(
    "",
    response_model=List[test_schema.Test],
    summary="Lấy tất cả bài kiểm tra (áp dụng phân quyền theo vai trò)",
    dependencies=[Depends(get_current_active_user)]
)
def get_all_tests(
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    """
    Trả về danh sách bài kiểm tra đã được lọc theo vai trò của người dùng hiện tại (Manager/Teacher/Student/Parent).
    """
    print("Current user roles:", current_user.roles)
    return test_crud.get_all_tests(db, current_user, skip=skip, limit=limit)


@router.get(
    "/{test_id}", 
    response_model=test_schema.Test,
    summary="Lấy thông tin của một bản ghi bài kiểm tra cụ thể bằng ID",
    dependencies=[Depends(get_current_active_user)]
)
def get_test(
    test_id: int, 
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Lấy thông tin bài kiểm tra theo ID.
    Teacher chỉ được xem bài kiểm tra của lớp mình dạy.
    """
    db_test = test_crud.get_test(db, test_id=test_id, current_user=current_user)
    if db_test is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bài kiểm tra không tìm thấy hoặc bạn không có quyền xem."
        )
    return db_test

# --- ENDPOINT: Lấy bài kiểm tra theo Học sinh ---
@router.get(
    "/student/{student_user_id}",
    response_model=List[test_schema.Test],
    summary="Lấy tất cả bài kiểm tra của một học sinh",
    dependencies=[MANAGER_OR_TEACHER] # SỬ DỤNG TRỰC TIẾP
)
def get_tests_for_student(
    student_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    # Hiện tại, ta chỉ gọi hàm CRUD đã có sẵn:
    tests = test_crud.get_tests_by_student_user_id(db, student_user_id, skip=skip, limit=limit)
    
    return tests

# --- ENDPOINT: Lấy bài kiểm tra theo Giáo viên ---
@router.get(
    "/teacher/{teacher_user_id}",
    response_model=List[test_schema.Test],
    summary="Lấy tất cả bài kiểm tra của các lớp do một giáo viên giảng dạy",
    dependencies=[MANAGER_ONLY] # SỬ DỤNG TRỰC TIẾP
)
def get_tests_for_teacher(
    teacher_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    """
    Trả về danh sách bài kiểm tra của các lớp do giáo viên này giảng dạy.
    Giới hạn quyền truy cập: Chỉ Manager, hoặc chính Giáo viên đó mới được xem.
    """
    
    # Kiểm tra quyền: Chỉ Manager hoặc chính Teacher đó mới được phép truy vấn.
    if "manager" not in current_user.roles and current_user.user_id != teacher_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem bài kiểm tra của giáo viên này."
        )

    tests = test_crud.get_tests_by_teacher_user_id(db, teacher_user_id, skip=skip, limit=limit)
    
    return tests


@router.put(
    "/{test_id}",
    response_model=test_schema.Test,
    summary="Cập nhật một bài kiểm tra",
    dependencies=[MANAGER_OR_TEACHER] # ĐÃ SỬA: Sử dụng trực tiếp biến dependency
)
def update_existing_test(
    test_id: int,
    test_update: test_schema.TestUpdate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user)
):
    db_test = test_crud.get_test(db, test_id=test_id, current_user=current_user)
    if not db_test:
        raise HTTPException(status_code=404, detail="Bài kiểm tra không tìm thấy.")

    updated_test = test_crud.update_test(db, test_id, test_update, current_user=current_user)
    if not updated_test:
        raise HTTPException(status_code=400, detail="Không thể cập nhật bài kiểm tra.")

    return updated_test

@router.delete(
    "/{test_id}", 
    summary="Xóa một bản ghi bài kiểm tra cụ thể bằng ID",
    status_code=status.HTTP_200_OK,
    dependencies=[MANAGER_OR_TEACHER] # ĐÃ SỬA: Sử dụng trực tiếp biến dependency
)
def delete_existing_test(
    test_id: int, 
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Xóa một bản ghi bài kiểm tra theo ID.
    - Manager: xóa bất kỳ
    - Teacher: chỉ xóa được test của lớp mình
    """
    deleted_test = test_crud.delete_test(db, test_id, current_user)
    if not deleted_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bài kiểm tra không tìm thấy hoặc bạn không có quyền xóa."
        )
    return {
        "message": "Bài kiểm tra đã được xóa thành công.",
        "deleted_test_id": deleted_test.test_id,
        "status": "success"
    }

@router.post(
    "/import",
    summary="Import danh sách điểm kiểm tra từ file Excel vào DB",
    dependencies=[MANAGER_OR_TEACHER] # ĐÃ SỬA: Sử dụng trực tiếp biến dependency
)
def import_tests_endpoint(
    class_id: int = Query(..., description="ID của lớp cần import bài kiểm tra"),
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Import danh sách điểm kiểm tra từ file Excel vào DB.
    
    Quyền truy cập: **manager**, **teacher**
    """
    try:
        # Kiểm tra sự tồn tại của class_id trước khi import
        db_class = class_crud.get_class(db, class_id=class_id)
        if not db_class:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class with id {class_id} not found."
            )
            
        result = import_tests_from_excel(db, file, class_id, current_user)
        return {"message": "Import thành công", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
