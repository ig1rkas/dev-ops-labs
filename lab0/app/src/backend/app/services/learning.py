from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import ChatMessage
from app.models.learning import CourseRequest, Lesson, TeacherStudentAssignment
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.schemas.learning import CourseRequestCreate, ScheduleLessonCreate
from app.services.messaging import ensure_direct_chat, ensure_support_chat, get_chat_detail


def teacher_profile_for_user(db: Session, user: User) -> Teacher | None:
    return db.execute(
        select(Teacher)
        .options(
            joinedload(Teacher.subject),
            joinedload(Teacher.subject_assignments).joinedload(TeacherSubject.subject),
        )
        .where(Teacher.name == user.full_name)
        .order_by(Teacher.id)
    ).unique().scalars().first()


def teacher_user_for_profile(db: Session, teacher: Teacher) -> User | None:
    return db.scalar(select(User).where(User.role == "teacher", User.full_name == teacher.name).order_by(User.id))


def teacher_can_teach_subject(teacher: Teacher, subject_id: int) -> bool:
    if teacher.subject_id == subject_id:
        return True
    return any(assignment.subject_id == subject_id for assignment in teacher.subject_assignments or [])


def course_request_to_read(request: CourseRequest) -> dict:
    student_name = request.contact_name or (request.student.full_name if request.student is not None else "Без имени")
    student_email = request.student.email if request.student is not None else None
    return {
        "id": request.id,
        "status": request.status,
        "note": request.note,
        "student_id": request.student_id,
        "student_name": student_name,
        "student_email": student_email,
        "contact_name": student_name,
        "contact_method": request.contact_method or ("email" if student_email else "unknown"),
        "contact_value": request.contact_value or student_email or "не указан",
        "subject_id": request.subject_id,
        "subject_slug": request.subject.slug,
        "subject_title": request.subject.title,
        "teacher_id": request.teacher_id,
        "teacher_name": request.teacher.name if request.teacher is not None else None,
        "chat_id": request.chat_id,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }


def get_course_request(db: Session, request_id: int) -> CourseRequest:
    request = db.execute(
        select(CourseRequest)
        .options(joinedload(CourseRequest.student), joinedload(CourseRequest.subject), joinedload(CourseRequest.teacher), joinedload(CourseRequest.chat))
        .where(CourseRequest.id == request_id)
    ).unique().scalars().first()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return request


def create_course_request(db: Session, student: User | None, payload: CourseRequestCreate) -> dict:
    subject = db.scalar(select(Subject).where(Subject.slug == payload.subject_slug, Subject.is_active.is_(True)))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Предмет не найден")

    linked_student = student if student is not None and student.role == "student" else None
    chat = ensure_support_chat(db, linked_student) if linked_student is not None else None

    teacher = None
    if payload.teacher_id is not None:
        teacher = db.execute(
            select(Teacher)
            .options(joinedload(Teacher.subject_assignments), joinedload(Teacher.subject))
            .where(Teacher.id == payload.teacher_id, Teacher.account_disabled.is_(False))
        ).unique().scalars().first()
        if teacher is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Преподаватель не найден")
        if not teacher_can_teach_subject(teacher, subject.id):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Преподаватель не ведёт выбранный предмет")

    request = CourseRequest(
        student_id=linked_student.id if linked_student is not None else None,
        subject_id=subject.id,
        teacher_id=teacher.id if teacher is not None else None,
        chat_id=chat.id if chat is not None else None,
        contact_name=payload.contact_name,
        contact_method=payload.contact_method,
        contact_value=payload.contact_value,
        note=payload.note,
        status="new",
    )
    db.add(request)
    db.flush()

    message = f"Заявка на предмет: {subject.title}."
    if teacher is not None:
        message += f" Преподаватель: {teacher.name}."
    if payload.note:
        message += f"\nКомментарий: {payload.note.strip()}"
    message += f"\nКонтакт: {payload.contact_method} — {payload.contact_value}. Имя: {payload.contact_name}."
    if chat is not None and linked_student is not None:
        db.add(ChatMessage(chat_id=chat.id, sender_id=linked_student.id, body=message))
    db.commit()
    db.refresh(request)

    request = get_course_request(db, request.id)
    chat_detail = get_chat_detail(db, linked_student, chat.id) if chat is not None and linked_student is not None else None
    return {"request": course_request_to_read(request), "chat": chat_detail}


def list_course_requests(db: Session, status_filter: str | None = None) -> list[dict]:
    stmt = (
        select(CourseRequest)
        .options(joinedload(CourseRequest.student), joinedload(CourseRequest.subject), joinedload(CourseRequest.teacher), joinedload(CourseRequest.chat))
        .order_by(CourseRequest.updated_at.desc(), CourseRequest.id.desc())
    )
    if status_filter and status_filter != "all":
        stmt = stmt.where(CourseRequest.status == status_filter)
    return [course_request_to_read(request) for request in db.execute(stmt).unique().scalars().all()]


def delete_course_request(db: Session, request_id: int) -> None:
    request = get_course_request(db, request_id)
    db.delete(request)
    db.commit()


def get_or_create_assignment(db: Session, teacher: Teacher, teacher_user: User, request: CourseRequest) -> TeacherStudentAssignment:
    assignment = db.scalar(
        select(TeacherStudentAssignment).where(
            TeacherStudentAssignment.teacher_id == teacher.id,
            TeacherStudentAssignment.teacher_user_id == teacher_user.id,
            TeacherStudentAssignment.student_id == request.student_id,
            TeacherStudentAssignment.subject_id == request.subject_id,
            TeacherStudentAssignment.status == "active",
        )
    )
    if assignment is not None:
        return assignment

    assignment = TeacherStudentAssignment(
        teacher_id=teacher.id,
        teacher_user_id=teacher_user.id,
        student_id=request.student_id,
        subject_id=request.subject_id,
        status="active",
    )
    db.add(assignment)
    db.flush()
    return assignment


WEEKDAY_NAMES = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")


def parse_slot_time(value: str) -> time:
    try:
        hour, minute = [int(part) for part in value.split(":", 1)]
        return time(hour=hour, minute=minute)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Некорректное время урока") from exc


def next_week_monday() -> datetime:
    today = datetime.now().date()
    days_until_next_monday = 7 - today.weekday()
    return datetime.combine(today + timedelta(days=days_until_next_monday), time.min)


def build_recurring_lesson_starts(payload: ScheduleLessonCreate) -> list[datetime]:
    if payload.slots:
        week_start = next_week_monday()
        lesson_starts = []
        for week_index in range(payload.weeks_count):
            week_base = week_start + timedelta(days=week_index * 7)
            for slot in payload.slots:
                starts_at = datetime.combine((week_base + timedelta(days=slot.weekday)).date(), parse_slot_time(slot.time))
                lesson_starts.append(starts_at)
        return sorted(lesson_starts)

    if payload.starts_at is not None:
        return [payload.starts_at]

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Добавьте хотя бы один день и время урока")


def format_schedule_summary(payload: ScheduleLessonCreate, lesson_starts: list[datetime]) -> str:
    if payload.slots:
        slots_text = ", ".join(f"{WEEKDAY_NAMES[slot.weekday]} {slot.time}" for slot in payload.slots)
        return f"{slots_text}; старт с {lesson_starts[0].strftime('%d.%m')}; всего занятий: {len(lesson_starts)}"
    return lesson_starts[0].strftime("%d.%m %H:%M")


def schedule_lesson_for_request(db: Session, admin: User, request_id: int, payload: ScheduleLessonCreate) -> dict:
    request = get_course_request(db, request_id)
    if request.student_id is None or request.student is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для назначения уроков сначала создайте ученика и свяжите его с заявкой",
        )
    teacher = db.execute(
        select(Teacher)
        .options(joinedload(Teacher.subject_assignments), joinedload(Teacher.subject))
        .where(Teacher.id == payload.teacher_id)
    ).unique().scalars().first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Преподаватель не найден")
    if not teacher_can_teach_subject(teacher, request.subject_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="У преподавателя нет этого предмета")

    teacher_user = teacher_user_for_profile(db, teacher)
    if teacher_user is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="У преподавателя нет аккаунта для входа")

    lesson_starts = build_recurring_lesson_starts(payload)
    schedule_summary = format_schedule_summary(payload, lesson_starts)
    assignment = get_or_create_assignment(db, teacher, teacher_user, request)
    # Persist the final selected teacher as well, including legacy subject-only
    # requests that were created before direct teacher booking was introduced.
    request.teacher_id = teacher.id
    for starts_at in lesson_starts:
        db.add(
            Lesson(
                assignment_id=assignment.id,
                teacher_id=teacher.id,
                teacher_user_id=teacher_user.id,
                student_id=request.student_id,
                subject_id=request.subject_id,
                starts_at=starts_at,
                duration_minutes=payload.duration_minutes,
                topic=payload.topic,
                status="online",
            )
        )
    request.status = "scheduled"

    direct_chat = ensure_direct_chat(db, teacher_user, request.student)
    db.add(ChatMessage(chat_id=direct_chat.id, sender_id=admin.id, body=f"Назначено расписание по курсу {request.subject.title}: {payload.topic}. {schedule_summary}."))
    if request.chat_id is not None:
        db.add(ChatMessage(chat_id=request.chat_id, sender_id=admin.id, body=f"Уроки назначены: {teacher.name}, {schedule_summary}, тема: {payload.topic}."))
    db.commit()
    db.refresh(request)
    return course_request_to_read(get_course_request(db, request.id))


def list_assignments_for_teacher(db: Session, teacher_user: User) -> list[TeacherStudentAssignment]:
    return list(
        db.scalars(
            select(TeacherStudentAssignment)
            .options(joinedload(TeacherStudentAssignment.student), joinedload(TeacherStudentAssignment.subject))
            .where(TeacherStudentAssignment.teacher_user_id == teacher_user.id, TeacherStudentAssignment.status == "active")
            .order_by(TeacherStudentAssignment.created_at.desc(), TeacherStudentAssignment.id.desc())
        )
    )


def list_student_ids_for_teacher(db: Session, teacher_user: User) -> list[int]:
    return list(
        db.scalars(
            select(TeacherStudentAssignment.student_id)
            .where(TeacherStudentAssignment.teacher_user_id == teacher_user.id, TeacherStudentAssignment.status == "active")
            .distinct()
        )
    )


def lesson_to_dashboard_item(lesson: Lesson) -> dict:
    starts_at = lesson.starts_at
    return {
        "id": lesson.id,
        "date": starts_at.date().isoformat(),
        "day_offset": starts_at.weekday(),
        "time": starts_at.strftime("%H:%M"),
        "duration": f"{lesson.duration_minutes} мин",
        "course": lesson.subject.title,
        "topic": lesson.topic,
        "status": lesson.status,
        "student": lesson.student.full_name,
        "teacher": lesson.teacher.name,
    }
