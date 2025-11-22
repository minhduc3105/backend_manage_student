# app/api/v1/api.py
from fastapi import APIRouter

# --- Import các routers chức năng chung ---
from app.api.v1.endpoints.user_route import router as user_router
from app.api.v1.endpoints.manager_route import router as manager_router
from app.api.v1.endpoints.payroll_route import router as payroll_router
from app.api.v1.endpoints.teacher_route import router as teacher_router
from app.api.v1.endpoints.parent_route import router as parent_router
from app.api.v1.endpoints.student_route import router as student_router
from app.api.v1.endpoints.subject_route import router as subject_router
from app.api.v1.endpoints.test_route import router as test_router
from app.api.v1.endpoints.tuition_route import router as tuition_router
from app.api.v1.endpoints.enrollment_route import router as enrollment_router
from app.api.v1.endpoints.class_route import router as class_router
from app.api.v1.endpoints.attendance_route import router as attendance_router
from app.api.v1.endpoints.evaluation_route import router as evaluation_router
from app.api.v1.endpoints.schedule_route import router as schedule_router
from app.api.v1.endpoints.teacher_review_route import router as teacher_review_router
from app.api.v1.endpoints.notification_route import router as notification_router
from app.api.v1.endpoints.report_route import router as report_router
# --- Import các routers đăng ký chuyên biệt ---
# Router cho việc đăng ký một người dùng duy nhất
from app.api.v1.endpoints.register_route import router as register_router
from app.api.v1.endpoints.auth_route import router as auth_router

api_router = APIRouter()

# --- Bao gồm các routers vào router chính ---
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(manager_router, prefix="/managers", tags=["Managers"])
api_router.include_router(payroll_router, prefix="/payrolls", tags=["Payrolls"])
api_router.include_router(teacher_router, prefix="/teachers", tags=["Teachers"])
api_router.include_router(parent_router, prefix="/parents", tags=["Parents"])
api_router.include_router(student_router, prefix="/students", tags=["Students"])
api_router.include_router(subject_router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(test_router, prefix="/tests", tags=["Tests"])
api_router.include_router(tuition_router, prefix="/tuitions", tags=["Tuitions"])
api_router.include_router(enrollment_router, prefix="/enrollments", tags=["Enrollments"])
api_router.include_router(class_router, prefix="/classes", tags=["Classes"])
api_router.include_router(attendance_router, prefix="/attendances", tags=["Attendances"])
api_router.include_router(evaluation_router, prefix="/evaluations", tags=["Evaluations"])
api_router.include_router(schedule_router, prefix="/schedules", tags=["Schedules"])
api_router.include_router(teacher_review_router, prefix="/teacher_reviews", tags=["Teacher Reviews"])
api_router.include_router(notification_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(report_router, prefix="/reports", tags=["Reports"])
# --- Bao gồm các routers đăng ký chuyên biệt ---
api_router.include_router(register_router, prefix="/register", tags=["Register"])
api_router.include_router(auth_router, prefix="/auth", tags=["Login"])