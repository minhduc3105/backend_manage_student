from sqlalchemy.orm import Session
from app.models.evaluation_model import Evaluation
from app.schemas.evaluation_schema import EvaluationCreate, EvaluationUpdate


def create_evaluation(db: Session, evaluation: EvaluationCreate, teacher_user_id: int):
    """
    Tạo mới một bản ghi đánh giá chi tiết (delta).
    
    Dữ liệu đầu vào:
    - evaluation.study_point: sự thay đổi điểm học tập (+5, -1, ...).
    - evaluation.discipline_point: sự thay đổi điểm kỷ luật (+10, -5, ...).
    - evaluation.evaluation_content: lý do thay đổi điểm.
    """
    db_evaluation = Evaluation(
        **evaluation.model_dump(),
        teacher_user_id=teacher_user_id
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation



def get_evaluation(db: Session, evaluation_id: int):
    return db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()


def update_evaluation(db: Session, evaluation_id: int, evaluation_update: EvaluationUpdate):
    db_evaluation = get_evaluation(db, evaluation_id)
    if not db_evaluation:
        return None
    for field, value in evaluation_update.dict(exclude_unset=True).items():
        setattr(db_evaluation, field, value)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation


def delete_evaluation(db: Session, evaluation_id: int):
    db_evaluation = get_evaluation(db, evaluation_id)
    if not db_evaluation:
        return {"message": "Evaluation not found."}
    db.delete(db_evaluation)
    db.commit()
    return {"message": "Đã xóa thành công"}
