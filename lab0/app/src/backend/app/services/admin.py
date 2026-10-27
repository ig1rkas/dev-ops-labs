from fastapi import HTTPException
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.learning import CourseRequest, HomeworkItem, Lesson, TeacherStudentAssignment
from app.models.student_dashboard import StudentDashboard
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_application import TeacherApplication
from app.models.teacher_subject import TeacherSubject
from app.models.telegram import TelegramChat
from app.models.user import User
from app.schemas.admin import AdminTeacherReorder, AdminTeacherUpdate
from app.schemas.subject import AdminSubjectCreate
from app.services.auth import get_user_by_email, hash_password, verify_password
from app.services.google_calendar import normalize_google_calendar_url


def ensure_admin_account(db: Session) -> User:
    admin = get_user_by_email(db, settings.admin_email)
    if admin is not None:
        # Keep the configured development/admin credentials usable after an
        # old Docker volume is reused. Custom deployments can set their own
        # ADMIN_PASSWORD through the environment.
        changed = False
        if admin.role != "admin":
            admin.role = "admin"
            changed = True
        if not verify_password(settings.admin_password, admin.password_hash):
            admin.password_hash = hash_password(settings.admin_password)
            changed = True
        if changed:
            db.commit()
            db.refresh(admin)
        return admin

    admin = User(
        email=settings.admin_email.lower(),
        full_name=settings.admin_name,
        role="admin",
        password_hash=hash_password(settings.admin_password),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def ensure_test_teacher_account(db: Session) -> User | None:
    """Create a deterministic teacher account for local/demo installations."""

    email = settings.test_teacher_email.lower()
    password = settings.test_teacher_password
    user = get_user_by_email(db, email)
    profile = db.scalar(select(Teacher).where(Teacher.name == settings.test_teacher_name).order_by(Teacher.id))
    if user is None and profile is not None and profile.account_disabled:
        # An administrator intentionally removed this account; do not restore
        # it automatically on the next Docker restart.
        return None
    if user is None:
        user = User(
            email=email,
            full_name=settings.test_teacher_name,
            role="teacher",
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if user.role != "teacher":
            user.role = "teacher"
            changed = True
        if user.full_name != settings.test_teacher_name:
            user.full_name = settings.test_teacher_name
            changed = True
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
    # The dashboard resolves a public profile by the teacher's full name.
    # Ensure the demo login has one as well, otherwise the account technically
    # logs in but opens an empty/partially broken teacher cabinet.
    profile = db.scalar(select(Teacher).where(Teacher.name == user.full_name).order_by(Teacher.id))
    if profile is None:
        subject = db.scalar(select(Subject).order_by(Subject.id))
        if subject is not None:
            db.add(
                Teacher(
                    name=user.full_name,
                    role="Тестовый преподаватель",
                    description="Демонстрационный аккаунт преподавателя для проверки кабинета.",
                    rating=4.9,
                    initials="ТП",
                    subject_id=subject.id,
                    account_email=email,
                    sort_order=(db.scalar(select(func.max(Teacher.sort_order))) or 0) + 1,
                )
            )
            db.commit()
    elif not profile.account_email:
        profile.account_email = email
        db.commit()
    return user


def ensure_teacher_accounts(db: Session) -> None:
    """Create stable demo logins for every public teacher card.

    Credentials are deterministic and intended for local/demo use. Existing
    accounts are never overwritten, and accounts explicitly removed by an
    administrator are marked on the profile so they stay removed.
    """
    changed = False
    for profile in db.scalars(select(Teacher).order_by(Teacher.id)).all():
        if profile.account_disabled:
            continue
        email = profile.account_email or f"teacher-{profile.id}@idioma.school"
        if profile.account_email != email:
            profile.account_email = email
            changed = True
        account = get_user_by_email(db, email)
        if account is None:
            account = User(
                email=email,
                full_name=profile.name,
                role="teacher",
                password_hash=hash_password(f"Teacher{profile.id}123!"),
            )
            db.add(account)
            changed = True
        elif account.role != "teacher":
            account.role = "teacher"
            changed = True
    if changed:
        db.commit()


def count_today_lessons(db: Session) -> int:
    from datetime import datetime
    today = datetime.now().date()
    real_lessons = db.scalars(select(Lesson)).all()
    if real_lessons:
        return sum(1 for lesson in real_lessons if lesson.starts_at.date() == today)

    today_offset = (datetime.now().weekday()) % 7
    dashboards = db.scalars(select(StudentDashboard)).all()
    total = 0
    for dashboard in dashboards:
        for lesson in dashboard.lessons or []:
            if int(lesson.get("day_offset", -1)) == today_offset:
                total += 1
    return total


def build_admin_dashboard(db: Session) -> dict:
    students_count = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
    teacher_accounts_count = db.scalar(select(func.count(User.id)).where(User.role == "teacher")) or 0
    public_teachers_count = db.scalar(select(func.count(Teacher.id))) or 0
    subjects_count = db.scalar(select(func.count(Subject.id))) or 0
    # The dashboard chat metric must reflect real Telegram conversations. The
    # legacy website Chat table contains support-room records and made this
    # number unrelated to the Telegram inbox.
    chats_count = db.scalar(select(func.count(TelegramChat.id))) or 0
    course_requests_count = db.scalar(select(func.count(CourseRequest.id)).where(CourseRequest.status == "new")) or 0
    teacher_applications_count = db.scalar(
        select(func.count(TeacherApplication.id)).where(TeacherApplication.status == "new")
    ) or 0
    requests_count = course_requests_count + teacher_applications_count
    lessons_today = count_today_lessons(db)

    return {
        "summary": {
            "eyebrow": "Панель администратора",
            "greeting": "Администрирование idioma",
            "text": "Сводка по пользователям, преподавателям, занятиям и обращениям в поддержку.",
            "streak": {"value": chats_count, "unit": "чатов", "label": "в системе", "icon": "chat"},
        },
        "stats": [
            {"id": "students", "value": str(students_count), "label": "учеников", "icon": "users"},
            {"id": "teachers", "value": str(teacher_accounts_count), "label": "аккаунтов учителей", "icon": "graduation"},
            {"id": "public_teachers", "value": str(public_teachers_count), "label": "карточек преподавателей", "icon": "profile"},
            {"id": "lessons_today", "value": str(lessons_today), "label": "занятий сегодня", "icon": "calendar"},
            {"id": "subjects", "value": str(subjects_count), "label": "предметов", "icon": "books"},
            {"id": "chats", "value": str(chats_count), "label": "чатов", "icon": "chat"},
            {"id": "requests", "value": str(requests_count), "label": "новых заявок", "icon": "document"},
        ],
    }


def list_admin_users(db: Session, role: str | None = None, q: str | None = None) -> list[User]:
    stmt = select(User)
    if role and role != "all":
        stmt = stmt.where(User.role == role)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.full_name.ilike(like))
            | (User.email.ilike(like))
            | (User.telegram_username.ilike(like))
            | cast(User.telegram_user_id, String).ilike(like)
        )
    if role == "teacher":
        teacher_order_by_email = (
            select(Teacher.sort_order)
            .where(Teacher.account_email == User.email)
            .order_by(Teacher.id)
            .limit(1)
            .scalar_subquery()
        )
        teacher_order_by_name = (
            select(Teacher.sort_order)
            .where(Teacher.name == User.full_name)
            .order_by(Teacher.id)
            .limit(1)
            .scalar_subquery()
        )
        stmt = stmt.order_by(
            func.coalesce(teacher_order_by_email, teacher_order_by_name, 2_147_483_647),
            User.id,
        )
    else:
        stmt = stmt.order_by(User.created_at.desc(), User.id.desc())
    return list(db.scalars(stmt))


def create_admin_subject(db: Session, payload: AdminSubjectCreate) -> Subject:
    slug = payload.slug.strip().lower()
    existing = db.scalar(select(Subject).where(Subject.slug == slug))
    if existing is not None and existing.is_active:
        raise HTTPException(status_code=409, detail="Предмет с таким slug уже существует")
    if existing is not None:
        for field, value in payload.model_dump(exclude={"slug"}).items():
            setattr(existing, field, value)
        existing.is_active = True
        subject = existing
    else:
        subject = Subject(**payload.model_dump(exclude={"slug"}), slug=slug)
        db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def delete_admin_subject(db: Session, subject_id: int) -> None:
    subject = db.get(Subject, subject_id)
    if subject is None or not subject.is_active:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    usage = []
    if db.scalar(select(Teacher.id).where(Teacher.subject_id == subject_id).limit(1)) is not None or db.scalar(
        select(TeacherSubject.id).where(TeacherSubject.subject_id == subject_id).limit(1)
    ) is not None:
        usage.append("у преподавателей")
    if db.scalar(select(CourseRequest.id).where(CourseRequest.subject_id == subject_id).limit(1)) is not None:
        usage.append("в заявках")
    if db.scalar(
        select(TeacherStudentAssignment.id).where(TeacherStudentAssignment.subject_id == subject_id).limit(1)
    ) is not None:
        usage.append("в назначениях учеников")
    if db.scalar(select(Lesson.id).where(Lesson.subject_id == subject_id).limit(1)) is not None:
        usage.append("в расписании")
    if db.scalar(select(HomeworkItem.id).where(HomeworkItem.subject_id == subject_id).limit(1)) is not None:
        usage.append("в истории заданий")
    if usage:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя удалить предмет «{subject.title}»: он используется {' и '.join(usage)}. Сначала уберите связанные назначения.",
        )

    # Keep the slug in the database so a deleted built-in subject is not
    # re-created by the catalog seed on the next Docker restart.
    subject.is_active = False
    db.commit()


def _teacher_profile_for_account(db: Session, teacher_user: User) -> Teacher:
    profile = db.scalar(select(Teacher).where(Teacher.account_email == teacher_user.email).order_by(Teacher.id))
    if profile is None:
        profile = db.scalar(select(Teacher).where(Teacher.name == teacher_user.full_name).order_by(Teacher.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Профиль преподавателя не найден")
    return profile


def update_admin_teacher(db: Session, teacher_user_id: int, payload: AdminTeacherUpdate) -> User:
    teacher_user = db.get(User, teacher_user_id)
    if teacher_user is None or teacher_user.role != "teacher":
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    profile = _teacher_profile_for_account(db, teacher_user)
    slugs = list(dict.fromkeys(slug.strip().lower() for slug in payload.subject_slugs if slug.strip()))
    if not slugs:
        raise HTTPException(status_code=422, detail="Выберите хотя бы один предмет")
    subjects = list(db.scalars(select(Subject).where(Subject.slug.in_(slugs), Subject.is_active.is_(True))).all())
    subjects_by_slug = {subject.slug: subject for subject in subjects}
    missing = [slug for slug in slugs if slug not in subjects_by_slug]
    if missing:
        raise HTTPException(status_code=404, detail=f"Предмет не найден: {', '.join(missing)}")

    subjects = [subjects_by_slug[slug] for slug in slugs]
    try:
        calendar_url = normalize_google_calendar_url(payload.calendar_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    teacher_user.full_name = payload.full_name.strip()
    profile.name = teacher_user.full_name
    profile.role = payload.role.strip()
    profile.description = payload.description.strip()
    profile.rating = payload.rating
    profile.initials = (payload.initials or "").strip().upper()[:8] or profile.initials
    profile.lesson_price = payload.lesson_price
    profile.avatar_url = payload.avatar_url
    profile.calendar_url = calendar_url
    selected_ids = {subject.id for subject in subjects}
    profile.subject_id = subjects[0].id
    for assignment in list(profile.subject_assignments or []):
        if assignment.subject_id not in selected_ids:
            db.delete(assignment)
    existing_ids = {assignment.subject_id for assignment in profile.subject_assignments or []}
    for subject in subjects:
        if subject.id not in existing_ids:
            db.add(TeacherSubject(teacher_id=profile.id, subject_id=subject.id))
    db.commit()
    db.refresh(teacher_user)
    return teacher_user


def reorder_admin_teacher(db: Session, teacher_user_id: int, payload: AdminTeacherReorder) -> User:
    teacher_user = db.get(User, teacher_user_id)
    if teacher_user is None or teacher_user.role != "teacher":
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    profile = _teacher_profile_for_account(db, teacher_user)
    profiles = list(
        db.scalars(
            select(Teacher)
            .where(Teacher.account_disabled.is_(False))
            .order_by(Teacher.sort_order, Teacher.id)
        )
    )
    try:
        current_index = next(index for index, item in enumerate(profiles) if item.id == profile.id)
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail="Профиль преподавателя не найден") from exc

    target_index = {
        "first": 0,
        "up": max(0, current_index - 1),
        "down": min(len(profiles) - 1, current_index + 1),
    }[payload.action]
    if target_index != current_index:
        profiles.insert(target_index, profiles.pop(current_index))
    for position, item in enumerate(profiles, start=1):
        item.sort_order = position
    db.commit()
    db.refresh(teacher_user)
    return teacher_user


def user_to_admin_read(user: User, db: Session | None = None) -> dict:
    teacher_profile = None
    if db is not None and user.role == "teacher":
        profile = db.scalar(select(Teacher).where(Teacher.account_email == user.email).order_by(Teacher.id))
        if profile is None:
            profile = db.scalar(select(Teacher).where(Teacher.name == user.full_name).order_by(Teacher.id))
        if profile is not None:
            subject_items = []
            seen_subjects = set()
            for subject in [profile.subject, *(assignment.subject for assignment in profile.subject_assignments or [])]:
                if subject is None or subject.id in seen_subjects:
                    continue
                seen_subjects.add(subject.id)
                subject_items.append({"id": subject.id, "slug": subject.slug, "title": subject.title, "category": subject.category, "exam_type": subject.exam_type, "icon": subject.icon})
            teacher_profile = {
                "id": profile.id,
                "name": profile.name,
                "role": profile.role,
                "description": profile.description,
                "rating": float(profile.rating),
                "initials": profile.initials,
                "subject_id": profile.subject_id,
                "subject_title": profile.subject.title if profile.subject else "Предмет не указан",
                "subject_slug": profile.subject.slug if profile.subject else "",
                "subjects": subject_items,
                "categories": list(dict.fromkeys(item["category"] for item in subject_items)),
                "lesson_price": profile.lesson_price,
                "avatar_url": profile.avatar_url,
                "calendar_url": profile.calendar_url,
                "sort_order": profile.sort_order,
            }
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "telegram_user_id": user.telegram_user_id,
        "telegram_username": user.telegram_username,
        "created_at": user.created_at,
        "password_status": "Пароль задан" if user.password_hash else "Пароль не задан",
        "password_note": "Исходный пароль не хранится: доступен только хеш.",
        "teacher_profile": teacher_profile,
    }
