from typing import Dict, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.services.excel_services import import_users
# Import dependency factory
from app.api.auth.auth import has_roles
from app.schemas.user_schema import UserCreate, UserUpdate, UserOut, UserView, UserViewDetails
from app.crud import user_crud
from app.api.auth.auth import get_current_active_user
from app.schemas.auth_schema import AuthenticatedUser
from app.database import get_db
from app.models.user_model import User
from passlib.context import CryptContext # type: ignore

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Dependency cho quyền truy cập của Manager hoặc Teacher
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])

@router.post(
    "/",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một người dùng mới",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền tạo
)
def create_user_info(user: UserCreate, db: Session = Depends(deps.get_db)):
    """
    Tạo một người dùng mới trong cơ sở dữ liệu.

    Quyền truy cập: **manager**
    """
    return user_crud.create_user(db=db, user=user)

@router.get(
    "/",
    response_model=List[UserView],
    summary="Lấy danh sách tất cả người dùng",
    # dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    """
    Truy vấn danh sách người dùng với tùy chọn phân trang.

    Quyền truy cập: **manager**, **teacher**
    """
    return user_crud.get_users(db, skip=skip, limit=limit)

@router.get(
    "/{user_id}",
    response_model=UserViewDetails,
    summary="Lấy thông tin một người dùng bằng ID",
    dependencies=[Depends(MANAGER_OR_TEACHER)] # Chỉ manager và teacher có quyền xem
)
def get_user(user_id: int, db: Session = Depends(deps.get_db)):
    """
    Truy vấn thông tin chi tiết của một người dùng cụ thể.

    Quyền truy cập: **manager**, **teacher**
    """
    user = user_crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tìm thấy."
        )
    return user

@router.put(
    "/{user_id}",
    response_model=UserOut,
    summary="Cập nhật thông tin người dùng",
    dependencies=[Depends(get_current_active_user)] # Bất kỳ người dùng đã xác thực nào cũng có thể truy cập
)
def update_user_info(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Cập nhật thông tin của một người dùng đã tồn tại.
    - Manager có thể cập nhật thông tin của bất kỳ người dùng nào.
    - Các vai trò khác chỉ có thể cập nhật thông tin của chính mình.

    Quyền truy cập: **tất cả người dùng đã đăng nhập**
    """
    # Chỉ cho phép cập nhật nếu là manager HOẶC user đang cập nhật chính họ
    if "manager" not in current_user.roles and current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền cập nhật thông tin của người dùng khác."
        )

    updated_user = user_crud.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tìm thấy."
        )
    return updated_user

@router.delete(
    "/{user_id}",
    response_model=UserOut,
    summary="Xóa một người dùng",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền xóa
)
def delete_user_info(user_id: int, db: Session = Depends(deps.get_db)):
    """
    Xóa một người dùng cụ thể khỏi cơ sở dữ liệu.

    Quyền truy cập: **manager**
    """
    deleted_user = user_crud.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tìm thấy."
        )
    return deleted_user

class ImportUsersResponse(BaseModel):
    status: str
    imported: Dict[str, dict]

@router.post(
    "/import-users",
    response_model=ImportUsersResponse,
    summary="Import người dùng từ file Excel",
    dependencies=[Depends(MANAGER_ONLY)]
)
def import_users_from_sheet(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
):
    """
    Import thông tin người dùng từ một file Excel.
    """
    try:
        result = import_users.import_users(file, db)
        return {"status": "success", "imported": result}
    except Exception as e:
        logging.exception("Import failed")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.put("/{user_id}/password", status_code=200)
def update_password(
    user_id: int,
    body: UpdatePasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Xác thực mật khẩu cũ
    if not pwd_context.verify(body.old_password, user.password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không đúng")

    # Hash và cập nhật mật khẩu mới
    hashed = pwd_context.hash(body.new_password)
    user.password = hashed
    db.add(user)
    db.commit()
    return {"message": "Password updated successfully"}
