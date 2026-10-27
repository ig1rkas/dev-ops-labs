from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.user import User


def list_teacher_subjects(teacher: Teacher) -> list[Subject]:
    subjects_by_id: dict[int, Subject] = {}
    if teacher.subject is not None:
        subjects_by_id[teacher.subject.id] = teacher.subject

    for assignment in teacher.subject_assignments or []:
        if assignment.subject is not None:
            subjects_by_id[assignment.subject.id] = assignment.subject

    return list(subjects_by_id.values())


def find_teacher(
    db: Session,
    teacher_id: int | None = None,
    teacher_email: str | None = None,
    teacher_name: str | None = None,
) -> Teacher | None:
    stmt = select(Teacher).options(joinedload(Teacher.subject), joinedload(Teacher.subject_assignments).joinedload(TeacherSubject.subject))

    if teacher_id is not None:
        return db.execute(stmt.where(Teacher.id == teacher_id)).unique().scalars().first()

    if teacher_email:
        user = db.scalar(select(User).where(User.email == teacher_email.lower(), User.role == "teacher"))
        if user is None:
            return None
        return db.execute(stmt.where(Teacher.name == user.full_name).order_by(Teacher.id)).unique().scalars().first()

    if teacher_name:
        return db.execute(stmt.where(Teacher.name == teacher_name).order_by(Teacher.id)).unique().scalars().first()

    return None


def get_subject(db: Session, subject_slug: str) -> Subject | None:
    return db.scalar(select(Subject).where(Subject.slug == subject_slug))


def add_subject_to_teacher(db: Session, teacher: Teacher, subject: Subject) -> tuple[TeacherSubject | None, bool]:
    existing = db.scalar(
        select(TeacherSubject).where(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.subject_id == subject.id,
        )
    )
    if existing is not None:
        return existing, False

    assignment = TeacherSubject(teacher_id=teacher.id, subject_id=subject.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment, True


def ensure_primary_subject_assignment(db: Session, teacher: Teacher) -> None:
    exists = db.scalar(
        select(TeacherSubject).where(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.subject_id == teacher.subject_id,
        )
    )
    if exists is None:
        db.add(TeacherSubject(teacher_id=teacher.id, subject_id=teacher.subject_id))
        db.commit()

