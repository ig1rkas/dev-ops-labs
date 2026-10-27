import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.learning import TeacherStudentAssignment
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.telegram import TelegramMessage
from app.models.user import User
from app.schemas.admin import AdminStudentCreate, AdminTeacherCreate, TeacherStudentDisplayNameUpdate
from app.services.auth import get_user_by_email, hash_password
from app.services.google_calendar import normalize_google_calendar_url


def _initials_for_name(name: str) -> str:
    initials = "".join(part[0] for part in name.split() if part)[:4].upper()
    return initials or name[:2].upper()


def create_admin_teacher(db: Session, payload: AdminTeacherCreate) -> User:
    if get_user_by_email(db, str(payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже существует")
    slugs = list(dict.fromkeys(
        [slug.strip().lower() for slug in payload.subject_slugs if slug.strip()]
        + ([payload.subject_slug.strip().lower()] if payload.subject_slug else [])
    ))
    if not slugs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Выберите хотя бы один предмет")
    subjects = list(db.scalars(select(Subject).where(Subject.slug.in_(slugs), Subject.is_active.is_(True))).all())
    subjects_by_slug = {subject.slug: subject for subject in subjects}
    missing = [slug for slug in slugs if slug not in subjects_by_slug]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Предмет не найден: {', '.join(missing)}")
    subject = subjects_by_slug[slugs[0]]

    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name.strip(),
        role="teacher",
        password_hash=hash_password(payload.password),
    )
    try:
        calendar_url = normalize_google_calendar_url(payload.calendar_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    teacher = Teacher(
        name=user.full_name,
        role=payload.role.strip(),
        description=payload.description.strip(),
        rating=payload.rating,
        initials=(payload.initials or _initials_for_name(user.full_name)).strip().upper()[:8],
        subject_id=subject.id,
        account_email=user.email,
        lesson_price=payload.lesson_price,
        avatar_url=payload.avatar_url,
        calendar_url=calendar_url,
        sort_order=(db.scalar(select(func.max(Teacher.sort_order))) or 0) + 1,
    )
    db.add_all([user, teacher])
    db.flush()
    db.add_all(TeacherSubject(teacher_id=teacher.id, subject_id=subject_item.id) for subject_item in subjects)
    db.commit()
    db.refresh(user)
    return user


def delete_user_from_system(db: Session, user_id: int, admin: User) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить текущего администратора")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Администратор защищён от удаления")

    # Remove the student's local Telegram conversation and add a durable peer
    # exclusion.  Telegram itself is never modified.  The exclusion is needed
    # because MTProto dialog sync sees the same remote peer again on restart.
    from sqlalchemy import delete
    from app.models.auth_token import AuthToken
    from app.models.chat import ChatMessage, ChatParticipant
    from app.models.student_dashboard import StudentDashboard
    from app.models.telegram import TelegramChat, TelegramChatReadState, TelegramDeletedMessage, TelegramIgnoredChat, TelegramMessage
    from app.models.learning import CourseRequest, HomeworkItem, Lesson

    db.execute(delete(HomeworkItem).where((HomeworkItem.student_id == user_id) | (HomeworkItem.teacher_user_id == user_id)))
    db.execute(delete(Lesson).where((Lesson.student_id == user_id) | (Lesson.teacher_user_id == user_id)))
    db.execute(delete(TeacherStudentAssignment).where((TeacherStudentAssignment.student_id == user_id) | (TeacherStudentAssignment.teacher_user_id == user_id)))
    db.execute(delete(CourseRequest).where(CourseRequest.student_id == user_id))
    db.execute(delete(ChatMessage).where(ChatMessage.sender_id == user_id))
    db.execute(delete(ChatParticipant).where(ChatParticipant.user_id == user_id))
    db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
    db.execute(delete(StudentDashboard).where(StudentDashboard.user_id == user_id))
    if target.role == "student" and target.telegram_user_id is not None:
        chat_ids = set(
            db.scalars(
                select(TelegramChat.telegram_chat_id).where(
                    (TelegramChat.telegram_chat_id == target.telegram_user_id)
                    | TelegramChat.id.in_(
                        select(TelegramMessage.chat_id).where(
                            TelegramMessage.sender_telegram_id == target.telegram_user_id,
                        )
                    )
                )
            ).all()
        )
        chat_ids.add(int(target.telegram_user_id))
        existing_ignored = set(
            db.scalars(
                select(TelegramIgnoredChat.telegram_chat_id).where(
                    TelegramIgnoredChat.telegram_chat_id.in_(chat_ids)
                )
            ).all()
        )
        db.add_all(
            TelegramIgnoredChat(telegram_chat_id=telegram_chat_id)
            for telegram_chat_id in chat_ids
            if telegram_chat_id not in existing_ignored
        )
        chat_rows = db.scalars(
            select(TelegramChat).where(TelegramChat.telegram_chat_id.in_(chat_ids))
        ).all()
        local_chat_ids = [chat.id for chat in chat_rows]
        if local_chat_ids:
            db.execute(delete(TelegramChatReadState).where(TelegramChatReadState.chat_id.in_(local_chat_ids)))
            db.execute(delete(TelegramDeletedMessage).where(TelegramDeletedMessage.chat_id.in_(local_chat_ids)))
            db.execute(delete(TelegramMessage).where(TelegramMessage.chat_id.in_(local_chat_ids)))
            db.execute(delete(TelegramChat).where(TelegramChat.id.in_(local_chat_ids)))
    if target.role == "teacher":
        profiles = db.scalars(
            select(Teacher).where(
                (Teacher.account_email == target.email) | (Teacher.name == target.full_name)
            )
        ).all()
        for profile in profiles:
            if profile.account_email and profile.account_email == target.email:
                profile.account_disabled = True
            else:
                db.execute(delete(TeacherSubject).where(TeacherSubject.teacher_id == profile.id))
                db.delete(profile)
    db.delete(target)
    db.commit()


def create_admin_student(db: Session, payload: AdminStudentCreate) -> User:
    """Create a contact-style student account for a Telegram user."""

    existing = db.scalar(select(User).where(User.telegram_user_id == payload.telegram_user_id))
    if existing is not None:
        if existing.role != "student":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот Telegram ID уже связан с другим аккаунтом")
        existing.full_name = payload.full_name.strip()
        existing.telegram_username = payload.telegram_username
        db.commit()
        db.refresh(existing)
        return existing

    # Students do not need to log in, but the legacy user model requires a
    # unique email and password hash. Keep those values internal and stable.
    student = User(
        email=f"telegram-{payload.telegram_user_id}@students-idioma.com",
        full_name=payload.full_name.strip(),
        role="student",
        password_hash=hash_password(secrets.token_urlsafe(32)),
        telegram_user_id=payload.telegram_user_id,
        telegram_username=payload.telegram_username,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def _teacher_profile_for_user(db: Session, teacher_user: User) -> Teacher:
    profile = db.scalar(select(Teacher).where(Teacher.name == teacher_user.full_name).order_by(Teacher.id))
    if profile is not None:
        return profile

    subject = db.scalar(select(Subject).order_by(Subject.id))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="В системе нет предметов для назначения")
    profile = Teacher(
        name=teacher_user.full_name,
        role="Преподаватель",
        description="Профиль преподавателя",
        rating=0,
        initials=(teacher_user.full_name[:2] or "ПР"),
        subject_id=subject.id,
    )
    db.add(profile)
    db.flush()
    return profile


def assign_student_to_teacher(db: Session, teacher_user_id: int, student_id: int) -> dict:
    teacher_user = db.get(User, teacher_user_id)
    if teacher_user is None or teacher_user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Преподаватель не найден")
    student = db.get(User, student_id)
    if student is None or student.role != "student":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ученик не найден")
    if student.telegram_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="У ученика не указан Telegram ID")

    system_sender_ids = {
        value
        for value in db.scalars(
            select(TelegramMessage.sender_telegram_id).where(
                TelegramMessage.direction == "outbound",
                TelegramMessage.sender_telegram_id.is_not(None),
            )
        ).all()
        if value is not None
    }
    if student.telegram_user_id in system_sender_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Нельзя назначить системный Telegram-аккаунт как ученика",
        )

    teacher_profile = _teacher_profile_for_user(db, teacher_user)
    assignment = db.scalar(
        select(TeacherStudentAssignment).where(
            TeacherStudentAssignment.teacher_user_id == teacher_user.id,
            TeacherStudentAssignment.student_id == student.id,
        )
    )
    if assignment is None:
        assignment = TeacherStudentAssignment(
            teacher_id=teacher_profile.id,
            teacher_user_id=teacher_user.id,
            student_id=student.id,
            subject_id=teacher_profile.subject_id,
            status="active",
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
    elif assignment.status != "active":
        assignment.status = "active"
        db.commit()
        db.refresh(assignment)

    subject = db.get(Subject, assignment.subject_id)
    return {
        "assignment_id": assignment.id,
        "teacher_user_id": teacher_user.id,
        "student_id": student.id,
        "student_name": assignment.teacher_display_name or student.full_name,
        "original_name": student.full_name,
        "display_name": assignment.teacher_display_name,
        "student_email": student.email,
        "telegram_user_id": student.telegram_user_id,
        "telegram_username": student.telegram_username,
        "subject_title": subject.title if subject else "Предмет не указан",
    }


def remove_student_from_teacher(db: Session, teacher_user_id: int, assignment_id: int) -> None:
    """Deactivate one teacher/student link while preserving its history."""
    assignment = db.scalar(
        select(TeacherStudentAssignment).where(
            TeacherStudentAssignment.id == assignment_id,
            TeacherStudentAssignment.teacher_user_id == teacher_user_id,
            TeacherStudentAssignment.status == "active",
        )
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Назначение не найдено")
    assignment.status = "inactive"
    db.commit()


def list_teacher_students(db: Session, teacher_user_id: int) -> list[dict]:
    assignments = db.scalars(
        select(TeacherStudentAssignment)
        .where(
            TeacherStudentAssignment.teacher_user_id == teacher_user_id,
            TeacherStudentAssignment.status == "active",
        )
        .order_by(TeacherStudentAssignment.created_at.desc(), TeacherStudentAssignment.id.desc())
    ).all()
    result = []
    for assignment in assignments:
        student = db.get(User, assignment.student_id)
        subject = db.get(Subject, assignment.subject_id)
        if student is None:
            continue
        result.append(
            {
                "assignment_id": assignment.id,
                "teacher_user_id": teacher_user_id,
                "student_id": student.id,
                "student_name": assignment.teacher_display_name or student.full_name,
                "original_name": student.full_name,
                "display_name": assignment.teacher_display_name,
                "student_email": student.email,
                "telegram_user_id": student.telegram_user_id,
                "telegram_username": student.telegram_username,
                "subject_title": subject.title if subject else "Предмет не указан",
            }
        )
    return result


def update_teacher_student_display_name(
    db: Session,
    teacher_user: User,
    assignment_id: int,
    payload: TeacherStudentDisplayNameUpdate,
) -> dict:
    if teacher_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только преподаватель может менять отображаемое имя ученика",
        )
    assignment = db.scalar(
        select(TeacherStudentAssignment).where(
            TeacherStudentAssignment.id == assignment_id,
            TeacherStudentAssignment.teacher_user_id == teacher_user.id,
            TeacherStudentAssignment.status == "active",
        )
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ученик не назначен этому преподавателю")
    student = db.get(User, assignment.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ученик не найден")
    assignment.teacher_display_name = payload.display_name
    db.commit()
    db.refresh(assignment)
    subject = db.get(Subject, assignment.subject_id)
    return {
        "assignment_id": assignment.id,
        "student_id": student.id,
        "student_name": assignment.teacher_display_name or student.full_name,
        "original_name": student.full_name,
        "display_name": assignment.teacher_display_name,
        "subject_title": subject.title if subject else "Предмет не указан",
    }
