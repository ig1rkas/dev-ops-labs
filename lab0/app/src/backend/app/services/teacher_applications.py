from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.teacher_application import TeacherApplication
from app.schemas.teacher_application import TeacherApplicationCreate


def create_teacher_application(db: Session, payload: TeacherApplicationCreate) -> TeacherApplication:
    application = TeacherApplication(**payload.model_dump(), status="new")
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def list_teacher_applications(db: Session, status_filter: str | None = None) -> list[TeacherApplication]:
    stmt = select(TeacherApplication).order_by(TeacherApplication.created_at.desc(), TeacherApplication.id.desc())
    if status_filter and status_filter != "all":
        stmt = stmt.where(TeacherApplication.status == status_filter)
    return list(db.scalars(stmt))


def delete_teacher_application(db: Session, application_id: int) -> None:
    application = db.get(TeacherApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка преподавателя не найдена")
    db.delete(application)
    db.commit()

