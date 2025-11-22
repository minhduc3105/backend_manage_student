from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud import notification_crud
from app.api import deps
from app.schemas import notification_schema
from app.api.auth.auth import get_current_active_user, has_roles
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Endpoint mới
@router.get(
    "/",
    response_model=List[notification_schema.Notification],
    summary="Lấy danh sách thông báo theo quyền",
)
def get_all_notifications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Lấy danh sách thông báo dựa trên vai trò của người dùng.
    - **Manager**: Trả về tất cả các thông báo.
    - **Các vai trò khác (ví dụ: teacher, student)**: Chỉ trả về các thông báo mà người dùng đó là người nhận.
    
    Quyền truy cập: **mọi vai trò đã đăng nhập**
    """
    if "manager" in current_user.roles:
        return notification_crud.get_all_notifications(db, skip=skip, limit=limit)
    else:
        return notification_crud.get_notifications_by_receiver_id(
            db, receiver_id=current_user.user_id, skip=skip, limit=limit
        )

# Existing endpoints
@router.post(
    "/",
    response_model=notification_schema.Notification,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một thông báo mới",
    dependencies=[Depends(MANAGER_ONLY)],
)
def create_new_notification(
    notification_in: notification_schema.NotificationCreate,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    # Thêm sender_id vào notification_in
    notification_in.sender_id = current_user.user_id
    db_notification = notification_crud.create_notification(db, notification=notification_in)
    return db_notification


@router.put(
    "/{notification_id}",
    response_model=notification_schema.Notification,
    summary="Cập nhật trạng thái thông báo",
    dependencies=[Depends(MANAGER_ONLY)],
)
def update_existing_notification(
    notification_id: int,
    notification_update: notification_schema.NotificationUpdate,
    db: Session = Depends(deps.get_db),
):
    db_notification = notification_crud.get_notification(db, notification_id)
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo",
        )
    return notification_crud.update_notification(db, notification_id, notification_update)


@router.get(
    "/{notification_id}",
    response_model=notification_schema.Notification,
    summary="Lấy thông tin chi tiết một thông báo",
)
def get_notification_by_id(
    notification_id: int,
    db: Session = Depends(deps.get_db)
):
    db_notification = notification_crud.get_notification(db, notification_id)
    if not db_notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    return db_notification


@router.delete(
    "/{notification_id}",
    response_model=dict,
    summary="Xóa một thông báo",
    dependencies=[Depends(MANAGER_ONLY)]
)
def delete_existing_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db)
):
    db_notification = notification_crud.get_notification(db, notification_id)
    if not db_notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    
    notification_crud.delete_notification(db, notification_id)
    return {"message": "Xóa thông báo thành công"}

@router.put(
    "/{notification_id}/read",
    response_model=notification_schema.NotificationRead,
    summary="Cập nhật trạng thái đã đọc của thông báo",
)
def update_notification_read_status(
    notification_id: int,
    is_read: bool,  # Tham số để xác định trạng thái mới
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Cập nhật trạng thái `is_read` của một thông báo. 
    Người dùng chỉ có thể cập nhật trạng thái của thông báo dành cho chính họ.
    """
    db_notification = notification_crud.get_notification(db, notification_id)
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo",
        )

    # Đảm bảo người dùng chỉ được cập nhật thông báo của chính họ
    if db_notification.receiver_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền cập nhật thông báo này",
        )

    return notification_crud.update_is_read_status(db, notification_id, is_read=is_read)