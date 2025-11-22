# app/api/routes/report_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.api.auth.auth import has_roles, get_current_active_user
from app.api import deps
from app.schemas.auth_schema import AuthenticatedUser
from app.schemas.report_schema import TeacherOverview,ClassReport,TeacherReport
from app.services import report_service
from app.api.deps import get_db

router = APIRouter() 
TEACHER_ONLY = has_roles(["teacher"])

@router.get("/teacher-overview", response_model=TeacherOverview, dependencies=[Depends(TEACHER_ONLY)])
def get_teacher_overview(
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    try:
        return report_service.get_teacher_overview(db, current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/class-report", response_model=ClassReport, dependencies=[Depends(TEACHER_ONLY)])
def get_class_report(
    class_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
) -> ClassReport:
    """
    Lấy báo cáo chi tiết của lớp thuộc giáo viên.
    """
    try:
        # Chỉ lấy lớp thuộc giáo viên
        teacher_id = current_user.user_id
        report = report_service.get_class_report(db, class_id, teacher_id)
        if not report:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp hoặc không có quyền truy cập")
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teacher-report", response_model=TeacherReport)
def teacher_report(
    teacher_id: int = Query(..., description="ID của giáo viên"),
    year: int = Query(datetime.now().year, description="Năm muốn xem báo cáo"),
    db: Session = Depends(get_db)
):
    
    try:
        report = report_service.get_teacher_report(db, teacher_id, year)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))