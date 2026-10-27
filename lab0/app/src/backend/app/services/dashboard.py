from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.learning import CourseRequest, Lesson, TeacherStudentAssignment
from app.models.student_dashboard import StudentDashboard
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.schemas.dashboard import StudentDashboardSettingsUpdate
from app.services.learning import lesson_to_dashboard_item, list_assignments_for_teacher
from app.services.google_calendar import load_google_calendar_lessons


def get_or_create_student_dashboard(db: Session, user: User) -> StudentDashboard:
    dashboard = db.scalar(select(StudentDashboard).where(StudentDashboard.user_id == user.id))
    if dashboard is not None:
        if ensure_week_schedule(dashboard):
            db.commit()
            db.refresh(dashboard)
        apply_student_learning_data(db, user, dashboard)
        return dashboard

    dashboard = StudentDashboard(user_id=user.id, **build_default_dashboard(db, user))
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    apply_student_learning_data(db, user, dashboard)
    return dashboard


def apply_student_learning_data(db: Session, user: User, dashboard: StudentDashboard) -> None:
    assignments = list(
        db.scalars(
            select(TeacherStudentAssignment)
            .options(joinedload(TeacherStudentAssignment.subject), joinedload(TeacherStudentAssignment.teacher))
            .where(TeacherStudentAssignment.student_id == user.id, TeacherStudentAssignment.status == "active")
            .order_by(TeacherStudentAssignment.created_at.desc(), TeacherStudentAssignment.id.desc())
        )
    )
    requests = list(
        db.scalars(
            select(CourseRequest)
            .options(joinedload(CourseRequest.subject))
            .where(CourseRequest.student_id == user.id, CourseRequest.status != "scheduled")
            .order_by(CourseRequest.created_at.desc(), CourseRequest.id.desc())
        )
    )
    lessons = list(
        db.scalars(
            select(Lesson)
            .options(joinedload(Lesson.subject), joinedload(Lesson.student), joinedload(Lesson.teacher))
            .where(Lesson.student_id == user.id)
            .order_by(Lesson.starts_at, Lesson.id)
        )
    )
    dynamic_courses = [
        {
            "id": assignment.id,
            "slug": assignment.subject.slug,
            "title": assignment.subject.title,
            "subtitle": f"Преподаватель: {assignment.teacher.name}",
            "progress": 0,
            "icon": assignment.subject.icon,
        }
        for assignment in assignments
    ]
    dynamic_courses.extend(
        {
            "id": f"request-{request.id}",
            "slug": request.subject.slug,
            "title": request.subject.title,
            "subtitle": "Заявка на согласовании",
            "progress": 0,
            "icon": request.subject.icon,
        }
        for request in requests
    )

    # Homework assignment/checking was removed from the product. Clear any
    # legacy JSON snapshot before returning the student dashboard.
    dashboard.homework = []
    if dynamic_courses or lessons:
        dashboard.courses = dynamic_courses
        dashboard.lessons = [lesson_to_dashboard_item(lesson) for lesson in lessons]
        dashboard.stats = [
            {"id": "weekly_lessons", "value": str(len(lessons)), "label": "занятий в расписании", "icon": "play"},
            {"id": "study_time", "value": f"{sum(lesson.duration_minutes for lesson in lessons) // 60} ч", "label": "запланировано", "icon": "clock"},
            {"id": "success", "value": str(len(assignments)), "label": "активных предметов", "icon": "chart"},
        ]


def update_student_dashboard_settings(
    db: Session,
    user: User,
    payload: StudentDashboardSettingsUpdate,
) -> StudentDashboard:
    dashboard = get_or_create_student_dashboard(db, user)
    data = payload.model_dump(exclude_unset=True)
    settings = dict(dashboard.settings or {})
    profile = dict(settings.get("profile") or {})

    if "full_name" in data and data["full_name"] is not None:
        full_name = data["full_name"].strip()
        if full_name:
            user.full_name = full_name
            profile["name"] = full_name
            summary = dict(dashboard.summary or {})
            first_name = full_name.split()[0]
            summary["greeting"] = f"Привет, {first_name}!"
            dashboard.summary = summary

    for key in ("notifications", "weekly_digest", "lesson_reminders"):
        if key in data and data[key] is not None:
            settings[key] = data[key]

    if "timezone" in data and data["timezone"] is not None:
        timezone = data["timezone"].strip()
        if timezone:
            settings["timezone"] = timezone

    profile["email"] = user.email
    profile["role"] = user.role
    settings["profile"] = profile
    dashboard.settings = settings

    db.commit()
    db.refresh(dashboard)
    return dashboard


def build_default_dashboard(db: Session, user: User) -> dict:
    _ = db
    first_name = user.full_name.split()[0] if user.full_name else "ученик"

    return {
        "summary": {
            "eyebrow": "Личный кабинет ученика",
            "greeting": f"Привет, {first_name}!",
            "text": "Здесь появятся твои курсы, занятия и прогресс после начала обучения или записи на курс.",
            "streak": {"value": 0, "unit": "дней", "label": "серия занятий", "icon": "rating"},
        },
        "stats": [
            {"id": "weekly_lessons", "value": "0", "label": "занятий на неделе", "icon": "play"},
            {"id": "study_time", "value": "0 ч", "label": "время обучения", "icon": "clock"},
            {"id": "success", "value": "0%", "label": "успеваемость", "icon": "chart"},
        ],
        "courses": [],
        "lessons": [],
        "homework": [],
        "achievements": [],
        "settings": {
            "profile": {"name": user.full_name, "email": user.email, "role": user.role},
            "notifications": True,
            "weekly_digest": True,
            "lesson_reminders": True,
            "timezone": "Europe/Moscow",
        },
        "recommendation": {
            "title": "Начни бесплатно",
            "text": "Выбери преподавателя, чтобы мы собрали персональный план и первые занятия.",
            "button": "Начать бесплатно",
            "panda": "trophy",
        },
    }


def build_week_lessons(primary: dict, secondary: dict, third: dict) -> list[dict]:
    course_cycle = [primary, secondary, third, primary, secondary, third, primary]
    topics = [
        "Разбор домашнего задания",
        "Speaking practice",
        "Алгоритмы и массивы",
        "Практика с преподавателем",
        "Мини-тест и обратная связь",
        "Повторение сложных тем",
        "План на следующую неделю",
    ]
    times = ["10:00", "12:30", "16:00", "11:00", "15:30", "13:00", "18:00"]
    return [
        {
            "id": index + 1,
            "day_offset": index,
            "time": times[index],
            "duration": "60 мин",
            "course": course_cycle[index]["title"],
            "topic": topics[index],
            "status": "online",
        }
        for index in range(7)
    ]


def ensure_week_schedule(dashboard: StudentDashboard) -> bool:
    lessons = [dict(lesson) for lesson in (dashboard.lessons or [])]
    if not lessons:
        return False

    changed = False
    topics = [
        "Разбор домашнего задания",
        "Speaking practice",
        "Алгоритмы и массивы",
        "Практика с преподавателем",
        "Мини-тест и обратная связь",
        "Повторение сложных тем",
        "План на следующую неделю",
    ]
    times = ["10:00", "12:30", "16:00", "11:00", "15:30", "13:00", "18:00"]

    for index, lesson in enumerate(lessons):
        if "day_offset" not in lesson:
            lesson["day_offset"] = index % 7
            changed = True
        if "duration" not in lesson:
            lesson["duration"] = "60 мин"
            changed = True

    seed_lessons = list(lessons)
    while len(lessons) < 7:
        base = dict(seed_lessons[len(lessons) % len(seed_lessons)])
        base["id"] = len(lessons) + 1
        base["day_offset"] = len(lessons)
        base["time"] = times[len(lessons)]
        base["topic"] = topics[len(lessons)]
        base.setdefault("duration", "60 мин")
        base.setdefault("status", "online")
        lessons.append(base)
        changed = True

    if changed:
        dashboard.lessons = lessons
    return changed


def course_icon(course: Course) -> str:
    title = course.title.lower()
    category = course.category.lower()
    if "математ" in title:
        return "sum"
    if "информ" in title or "program" in category or "it" in category:
        return "code"
    if "англий" in title or "ielts" in title:
        return "language"
    if "unity" in title or "игр" in title:
        return "game"
    return "book"

def build_teacher_dashboard(db: Session, user: User, *, refresh_calendar: bool = False) -> dict:
    teacher = db.execute(
        select(Teacher)
        .options(
            joinedload(Teacher.subject),
            joinedload(Teacher.subject_assignments).joinedload(TeacherSubject.subject),
        )
        .where(Teacher.name == user.full_name)
        .order_by(Teacher.id)
    ).unique().scalars().first()
    first_name = user.full_name.split()[0] if user.full_name else "преподаватель"
    teacher_rating = float(teacher.rating) if teacher else 0.0

    subjects_by_id = {}
    if teacher and teacher.subject:
        subjects_by_id[teacher.subject.id] = teacher.subject
    if teacher:
        for assignment in teacher.subject_assignments or []:
            if assignment.subject:
                subjects_by_id[assignment.subject.id] = assignment.subject
    subjects = list(subjects_by_id.values())
    assignments = list_assignments_for_teacher(db, user)
    lessons = list(
        db.scalars(
            select(Lesson)
            .options(joinedload(Lesson.subject), joinedload(Lesson.student), joinedload(Lesson.teacher))
            .where(Lesson.teacher_user_id == user.id)
            .order_by(Lesson.starts_at, Lesson.id)
        )
    )
    calendar_result = (
        load_google_calendar_lessons(
            teacher.calendar_url,
            teacher.name,
            force_refresh=refresh_calendar,
        )
        if teacher
        else None
    )
    lesson_items = [lesson_to_dashboard_item(lesson) for lesson in lessons]
    if calendar_result is not None:
        lesson_items.extend(calendar_result.lessons)
    lesson_items.sort(key=lambda lesson: (lesson.get("date", ""), lesson.get("time", ""), str(lesson.get("id", ""))))
    courses = [
        {
            "id": subject.id,
            "slug": subject.slug,
            "title": subject.title,
            "subtitle": "Предмет преподавателя",
            "progress": 0,
            "icon": subject.icon,
            "lessons_count": 0,
            "rating": teacher_rating,
        }
        for subject in subjects
    ]

    return {
        "summary": {
            "eyebrow": "Личный кабинет преподавателя",
            "greeting": f"Здравствуйте, {first_name}!",
            "text": "Рабочая панель занятий, учеников, предметов и переписки.",
            "streak": {"value": len(subjects), "unit": "предметов", "label": "закреплено", "icon": "books"},
        },
        "stats": [
            {"id": "students", "value": str(len(assignments)), "label": "активных учеников", "icon": "users"},
            {"id": "week_lessons", "value": str(len(lesson_items)), "label": "занятий в расписании", "icon": "calendar"},
            {"id": "rating", "value": f"{teacher_rating:.1f}", "label": "рейтинг профиля", "icon": "rating"},
        ],
        "courses": courses,
        "lessons": lesson_items,
        "students": [
            {
                "assignment_id": assignment.id,
                "student_id": assignment.student_id,
                "student_name": assignment.teacher_display_name or assignment.student.full_name,
                "original_name": assignment.student.full_name,
                "display_name": assignment.teacher_display_name,
                "subject_title": assignment.subject.title,
                "subject_slug": assignment.subject.slug,
            }
            for assignment in assignments
        ],
        "settings": {
            "profile": {"name": user.full_name, "email": user.email, "role": user.role},
            "timezone": "Europe/Moscow",
            "calendar_sync": {
                "configured": bool(teacher and teacher.calendar_url),
                "status": "error" if calendar_result and calendar_result.error else "ready",
                "message": calendar_result.error if calendar_result else None,
            },
        },
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "role": teacher.role,
            "description": teacher.description,
            "rating": teacher_rating,
            "initials": teacher.initials,
            "subject_title": ", ".join(subject.title for subject in subjects) if subjects else None,
            "subject_slug": subjects[0].slug if subjects else None,
            "subjects": [
                {"id": subject.id, "slug": subject.slug, "title": subject.title, "icon": subject.icon}
                for subject in subjects
            ],
        }
        if teacher
        else None,
    }
