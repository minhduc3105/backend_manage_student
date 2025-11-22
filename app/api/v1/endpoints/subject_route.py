# app/api/v1/endpoints/subject_route.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

# Import dependency factory
from app.api.auth.auth import has_roles

from app.crud import subject_crud
from app.schemas import subject_schema
from app.api import deps

router = APIRouter()

# Dependency cho quyền truy cập của Manager
MANAGER_ONLY = has_roles(["manager"])

# Dependency cho quyền truy cập của Manager hoặc Teacher
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])

@router.post(
    "/", 
    response_model=subject_schema.Subject, 
    status_code=status.HTTP_201_CREATED,
    summary="Tạo một môn học mới",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền tạo
)
def create_new_subject(
    subject_in: subject_schema.SubjectCreate, 
    db: Session = Depends(deps.get_db)
):
    """
    Tạo một môn học mới.
    
    Quyền truy cập: **manager**
    """
    # Kiểm tra xem tên môn học đã tồn tại chưa
    db_subject = subject_crud.get_subject_by_name(db, name=subject_in.name)
    if db_subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên môn học đã tồn tại."
        )
    # Tạo môn học nếu tên chưa tồn tại
    return subject_crud.create_subject(db=db, subject=subject_in)

@router.get(
    "/", 
    response_model=List[subject_schema.Subject],
    summary="Lấy danh sách tất cả môn học",
)
def get_all_subjects(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy danh sách tất cả môn học.
    
    Quyền truy cập: **manager**, **teacher**
    """
    subjects = subject_crud.get_all_subjects(db, skip=skip, limit=limit)
    return subjects

@router.get(
    "/{subject_id}", 
    response_model=subject_schema.Subject,
    summary="Lấy thông tin của một môn học cụ thể bằng ID",
    dependencies=[Depends(MANAGER_OR_TEACHER)] # Manager và teacher có thể xem
)
def get_subject(
    subject_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Lấy thông tin của một môn học cụ thể bằng ID.
    
    Quyền truy cập: **manager**, **teacher**
    """
    db_subject = subject_crud.get_subject(db, subject_id=subject_id)
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Môn học không tìm thấy."
        )
    return db_subject

@router.put(
    "/{subject_id}", 
    response_model=subject_schema.Subject,
    summary="Cập nhật thông tin của một môn học",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền cập nhật
)
def update_existing_subject(
    subject_id: int, 
    subject_update: subject_schema.SubjectUpdate, 
    db: Session = Depends(deps.get_db)
):
    """
    Cập nhật thông tin của một môn học cụ thể bằng ID.
    
    Quyền truy cập: **manager**
    """
    db_subject = subject_crud.get_subject(db, subject_id=subject_id)
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Môn học không tìm thấy."
        )
    
    updated_subject = subject_crud.update_subject(db, db_obj=db_subject, obj_in=subject_update)
    return updated_subject

@router.delete(
    "/{subject_id}", 
    response_model=dict,
    summary="Xóa một môn học",
    dependencies=[Depends(MANAGER_ONLY)] # Chỉ manager mới có quyền xóa
)
def delete_existing_subject(
    subject_id: int, 
    db: Session = Depends(deps.get_db)
):
    """
    Xóa một môn học khỏi cơ sở dữ liệu.
    
    Quyền truy cập: **manager**
    """
    db_subject = subject_crud.get_subject(db, subject_id=subject_id)
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Môn học không tìm thấy."
        )

    deleted_subject = subject_crud.delete_subject(db, db_obj=db_subject)

    return {
        "deleted_subject": subject_schema.Subject.from_orm(deleted_subject).dict(),
        "deleted_at": datetime.utcnow().isoformat(),
        "status": "success"
    }