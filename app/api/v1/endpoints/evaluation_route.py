from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.auth.auth import has_roles, get_current_active_user
from app.crud import evaluation_crud, teacher_crud, student_crud
from app.schemas import evaluation_schema
from app.api import deps
from app.services import evaluation_service
from app.schemas.auth_schema import AuthenticatedUser

router = APIRouter()

MANAGER_ONLY = has_roles(["manager"])
TEACHER_ONLY = has_roles(["teacher"])
MANAGER_TEACHER_AND_STUDENT = has_roles(["manager", "teacher", "student"])
MANAGER_OR_TEACHER = has_roles(["manager", "teacher"])
BASE_USERS=has_roles(["manager", "teacher", "student", "parent"])
# ----------------- CREATE -----------------
@router.post(
    "/",
    response_model=evaluation_schema.Evaluation,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(TEACHER_ONLY)]
)
def create_new_evaluation_record(
    evaluation_in: evaluation_schema.EvaluationCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    db_teacher = teacher_crud.get_teacher(db, teacher_user_id=current_user.user_id)
    if not db_teacher:
        raise HTTPException(status_code=404, detail=f"Teacher {current_user.user_id} not found.")

    db_student = student_crud.get_student(db, student_user_id=evaluation_in.student_user_id)
    if not db_student:
        raise HTTPException(status_code=404, detail=f"Student {evaluation_in.student_user_id} not found.")

    allowed_students = teacher_crud.get_students(db, teacher_user_id=current_user.user_id)
    allowed_student_ids = [s.student_user_id for s in allowed_students]
    if evaluation_in.student_user_id not in allowed_student_ids:
        raise HTTPException(status_code=403, detail="Not allowed to evaluate this student.")



    return evaluation_crud.create_evaluation(
        db=db,
        evaluation=evaluation_in,
        teacher_user_id=current_user.user_id
    )

# ----------------- READ LIST -----------------
@router.get(
    "",
    response_model=List[evaluation_schema.EvaluationView],
    summary="Danh sách tất cả đánh giá",
    dependencies=[Depends(BASE_USERS)]
)
def get_evaluations_by_role(
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    # Manager: all
    if "manager" in current_user.roles:
        return evaluation_service.get_all_evaluations_with_names(db, skip=skip, limit=limit)

    # Teacher: only their evaluations
    if "teacher" in current_user.roles:
        return evaluation_service.get_evaluations_by_teacher_user_id(
            db, current_user.user_id, skip, limit, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
        )

    # Student: only own evaluations
    if "student" in current_user.roles:
        try:
            return evaluation_service.get_evaluations_by_student_user_id(
                db, current_user.user_id, skip, limit, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied.")
        
    # Parent: children's evaluations
    if "parent" in current_user.roles:
        try:
            return evaluation_service.get_parent_children_evaluation(
                db, current_user.user_id, skip, limit, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied.")

    raise HTTPException(status_code=403, detail="Permission denied.")

# ----------------- STUDENT TOTAL SCORE -----------------
@router.get(
    "/total_score/{student_user_id}",
    dependencies=[Depends(MANAGER_TEACHER_AND_STUDENT)]
)
def get_total_score_by_student(
    student_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    # If requester is student, they can only request their own score
    if "student" in current_user.roles and student_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own score.")
    try:
        return evaluation_service.calculate_total_points_for_student(
            db, student_user_id, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied.")

# ----------------- SINGLE EVALUATION -----------------
@router.get(
    "/{evaluation_id}",
    response_model=evaluation_schema.Evaluation,
    dependencies=[Depends(BASE_USERS)]
)
def get_evaluation_record(
    evaluation_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    ev = evaluation_crud.get_evaluation(db, evaluation_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation not found.")

    # If student, they may only access their own evaluation
    if "student" in current_user.roles and ev.student_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own evaluations.")

    return ev

# ----------------- STUDENT EVALUATIONS -----------------
@router.get(
    "/student/{student_user_id}",
    response_model=List[evaluation_schema.EvaluationView],
    dependencies=[Depends(MANAGER_TEACHER_AND_STUDENT)]
)
def get_evaluations_of_student(
    student_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    # If requester is student, only allow their own data
    if "student" in current_user.roles and student_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own evaluations.")
    try:
        return evaluation_service.get_evaluations_by_student_user_id(
            db, student_user_id, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied.")

# ----------------- DELETE -----------------
@router.delete(
    "/{evaluation_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(TEACHER_ONLY)]
)
def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user)
):
    return evaluation_crud.delete_evaluation(db, evaluation_id)

# ----------------- TEACHER EVALUATIONS -----------------
@router.get(
    "/teacher/{teacher_user_id}",
    response_model=List[evaluation_schema.EvaluationView],
    summary="Danh sách đánh giá của giáo viên",
    dependencies=[Depends(MANAGER_OR_TEACHER)]
)
def get_evaluations_of_teacher(
    teacher_user_id: int,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    # If a student somehow tries to call this endpoint, block them
    if "student" in current_user.roles:
        raise HTTPException(status_code=403, detail="Permission denied.")
    return evaluation_service.get_evaluations_by_teacher_user_id(
        db, teacher_user_id, skip, limit, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
    )


# ----------------- STUDENT IN CLASS -----------------
@router.get(
    "/student/{student_user_id}/class/{class_id}",
    response_model=List[evaluation_schema.EvaluationView],
    dependencies=[Depends(MANAGER_TEACHER_AND_STUDENT)]
)
def get_evaluations_of_student_in_class(
    student_user_id: int,
    class_id: int,
    db: Session = Depends(deps.get_db),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Endpoint lấy danh sách evaluations của học sinh trong lớp, có phân trang.
    """
    if "student" in current_user.roles and student_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own evaluations.")
    try:
        return evaluation_service.get_evaluations_by_student_in_class(
            db=db,
            student_user_id=student_user_id,
            class_id=class_id,
            skip=skip,
            limit=limit,
            requesting_user_id=current_user.user_id,
            requesting_user_roles=current_user.roles
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied.")


@router.get(
    "/student/{student_user_id}/class/{class_id}/summary",
    response_model=evaluation_schema.EvaluationSummary,
    dependencies=[Depends(MANAGER_TEACHER_AND_STUDENT)]
)
def get_evaluations_summary_of_student_in_class(
    student_user_id: int,
    class_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_active_user),
):
    if "student" in current_user.roles and student_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Students can only view their own summary.")
    try:
        return evaluation_service.get_evaluations_summary_of_student_in_class(
            db, student_user_id, class_id, requesting_user_id=current_user.user_id, requesting_user_roles=current_user.roles
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied.")
