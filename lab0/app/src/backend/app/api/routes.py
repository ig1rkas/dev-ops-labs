from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from urllib.parse import quote
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminDashboardRead,
    AdminStudentCreate,
    AdminTeacherCreate,
    AdminTeacherReorder,
    AdminTeacherUpdate,
    AdminTeacherStudentCreate,
    AdminTeacherStudentRead,
    TeacherStudentRead,
    AdminUserRead,
    ChangePasswordRequest,
    TeacherStudentDisplayNameUpdate,
)
from app.schemas.auth import AuthResponse, UserCreate, UserLogin, UserRead
from app.schemas.course import CourseRead
from app.schemas.dashboard import StudentDashboardRead, StudentDashboardSettingsUpdate, TeacherDashboardRead
from app.schemas.learning import CourseRequestCreate, CourseRequestRead, CourseRequestResponse, ScheduleLessonCreate
from app.schemas.teacher_application import TeacherApplicationCreate, TeacherApplicationRead
from app.schemas.telegram import TelegramChatDetailRead, TelegramChatRead, TelegramMessageCreate, TelegramStatusRead
from app.schemas.subject import AdminSubjectCreate, SubjectRead
from app.schemas.teacher import TeacherRead
from app.services.admin import build_admin_dashboard, create_admin_subject, delete_admin_subject, list_admin_users, reorder_admin_teacher, update_admin_teacher, user_to_admin_read
from app.services.admin_students import assign_student_to_teacher, create_admin_student, create_admin_teacher, delete_user_from_system, list_teacher_students, remove_student_from_teacher, update_teacher_student_display_name
from app.services.auth import change_user_password, get_user_by_token, login_user, register_user
from app.services.catalog import list_subjects, list_teachers, teacher_to_read
from app.services.courses import get_course_by_slug, list_courses
from app.services.dashboard import build_teacher_dashboard, get_or_create_student_dashboard, update_student_dashboard_settings
from app.services.learning import create_course_request, delete_course_request, list_course_requests, schedule_lesson_for_request
from app.services.teacher_applications import create_teacher_application, delete_teacher_application, list_teacher_applications
from app.services.telegram import delete_telegram_message, discover_legacy_telegram_photos, get_telegram_chat_detail, get_telegram_document, get_telegram_photo, image_mime_type, list_telegram_chats, refresh_telegram_reactions, send_telegram_document_message, send_telegram_message, send_telegram_photo_message, telegram_status

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходима авторизация")

    user = get_user_by_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        return None
    user = get_user_by_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена")
    return user


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужны права администратора")
    return user


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "idioma"}


@router.get("/subjects", response_model=list[SubjectRead])
def get_subjects(
    category: str | None = None,
    exam_type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    return list_subjects(db, category=category, exam_type=exam_type, q=q)


@router.post("/admin/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def post_admin_subject(payload: AdminSubjectCreate, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    return create_admin_subject(db, payload)


@router.delete("/admin/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    delete_admin_subject(db, subject_id)
    return None


@router.get("/teachers", response_model=list[TeacherRead])
def get_teachers(
    category: str | None = None,
    subject_slug: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    return [teacher_to_read(teacher) for teacher in list_teachers(db, category=category, subject_slug=subject_slug, q=q)]


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user, token = register_user(db, payload)
    return {"token": token, "user": user}


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user, token = login_user(db, payload)
    return {"token": token, "user": user}


@router.get("/auth/me", response_model=UserRead)
def get_me(user=Depends(get_current_user)):
    return user


@router.patch("/auth/password", response_model=UserRead)
def patch_password(payload: ChangePasswordRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return change_user_password(db, user, payload)


@router.get("/dashboard/student", response_model=StudentDashboardRead)
def get_student_dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужен аккаунт ученика")
    return get_or_create_student_dashboard(db, user)


@router.get("/dashboard/teacher", response_model=TeacherDashboardRead)
def get_teacher_dashboard(
    refresh_calendar: bool = False,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужен аккаунт преподавателя")
    return build_teacher_dashboard(db, user, refresh_calendar=refresh_calendar)


@router.get("/dashboard/admin", response_model=AdminDashboardRead)
def get_admin_dashboard(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return build_admin_dashboard(db)


@router.patch("/dashboard/student/settings", response_model=StudentDashboardRead)
def patch_student_dashboard_settings(
    payload: StudentDashboardSettingsUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_student_dashboard_settings(db, user, payload)


@router.get("/messages/chats", response_model=list[TelegramChatRead])
def get_message_chats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return list_telegram_chats(db, user)


@router.get("/messages/status", response_model=TelegramStatusRead)
def get_message_status(user=Depends(get_current_user)):
    return telegram_status(user)


@router.get("/messages/chats/{chat_id}", response_model=TelegramChatDetailRead)
async def get_message_chat(
    chat_id: int,
    limit: int = Query(default=200, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    await discover_legacy_telegram_photos(db, user, chat_id, limit=limit)
    await refresh_telegram_reactions(db, user, chat_id, limit=limit)
    return get_telegram_chat_detail(db, user, chat_id, limit=limit)


@router.post("/messages/chats/{chat_id}/messages", response_model=TelegramChatDetailRead)
async def post_message(chat_id: int, payload: TelegramMessageCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await send_telegram_message(db, user, chat_id, payload.body)


@router.post("/messages/chats/{chat_id}/photos", response_model=TelegramChatDetailRead)
async def post_chat_photo(
    chat_id: int,
    photo: UploadFile = File(...),
    caption: str = Form(default=""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(caption) > 1024:
        raise HTTPException(status_code=422, detail="Подпись слишком длинная")
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Выберите JPEG, PNG или WebP")
    data = await photo.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Фото должно быть не больше 10 МБ")
    if image_mime_type(data) != photo.content_type:
        raise HTTPException(status_code=415, detail="Файл не является фотографией")
    return await send_telegram_photo_message(db, user, chat_id, data, photo.filename or "photo.jpg", caption.strip())


@router.post("/messages/chats/{chat_id}/documents", response_model=TelegramChatDetailRead)
async def post_chat_document(
    chat_id: int,
    document: UploadFile = File(...),
    caption: str = Form(default=""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(caption) > 1024:
        raise HTTPException(status_code=422, detail="Подпись слишком длинная")
    data = await document.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Файл должен быть не больше 20 МБ")
    filename = (document.filename or "file").replace("\\", "/").split("/")[-1][:255] or "file"
    return await send_telegram_document_message(db, user, chat_id, data, filename, caption.strip())


@router.get("/messages/chats/{chat_id}/messages/{message_id}/photo")
async def get_chat_photo(
    chat_id: int, message_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    data, mime_type = await get_telegram_photo(db, user, chat_id, message_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/messages/chats/{chat_id}/messages/{message_id}/document")
async def get_chat_document(
    chat_id: int, message_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    data, mime_type, filename = await get_telegram_document(db, user, chat_id, message_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.delete("/messages/chats/{chat_id}/messages/{message_id}", response_model=TelegramChatDetailRead)
def delete_message(
    chat_id: int,
    message_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return delete_telegram_message(db, admin, chat_id, message_id)


@router.post("/course-requests", response_model=CourseRequestResponse, status_code=status.HTTP_201_CREATED)
def post_course_request(payload: CourseRequestCreate, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    return create_course_request(db, user, payload)


@router.post("/teacher-applications", response_model=TeacherApplicationRead, status_code=status.HTTP_201_CREATED)
def post_teacher_application(payload: TeacherApplicationCreate, db: Session = Depends(get_db)):
    return create_teacher_application(db, payload)


@router.get("/admin/users", response_model=list[AdminUserRead])
def get_admin_users(
    role: str | None = None,
    q: str | None = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return [user_to_admin_read(user, db) for user in list_admin_users(db, role=role, q=q)]


@router.get("/admin/users/{user_id}", response_model=AdminUserRead)
def get_admin_user(user_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user_to_admin_read(target, db)


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(user_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    delete_user_from_system(db, user_id, admin)
    return None


@router.post("/admin/teachers", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def post_admin_teacher(
    payload: AdminTeacherCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_to_admin_read(create_admin_teacher(db, payload), db)


@router.patch("/admin/teachers/{teacher_user_id}", response_model=AdminUserRead)
def patch_admin_teacher(
    teacher_user_id: int,
    payload: AdminTeacherUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_to_admin_read(update_admin_teacher(db, teacher_user_id, payload), db)


@router.patch("/admin/teachers/{teacher_user_id}/position", response_model=AdminUserRead)
def patch_admin_teacher_position(
    teacher_user_id: int,
    payload: AdminTeacherReorder,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_to_admin_read(reorder_admin_teacher(db, teacher_user_id, payload), db)


@router.post("/admin/students", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def post_admin_student(
    payload: AdminStudentCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_to_admin_read(create_admin_student(db, payload))


@router.get("/admin/teachers/{teacher_user_id}/students", response_model=list[AdminTeacherStudentRead])
def get_admin_teacher_students(
    teacher_user_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_teacher_students(db, teacher_user_id)


@router.post("/admin/teachers/{teacher_user_id}/students", response_model=AdminTeacherStudentRead)
def post_admin_teacher_student(
    teacher_user_id: int,
    payload: AdminTeacherStudentCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return assign_student_to_teacher(db, teacher_user_id, payload.student_id)


@router.delete("/admin/teachers/{teacher_user_id}/students/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_teacher_student(
    teacher_user_id: int,
    assignment_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    remove_student_from_teacher(db, teacher_user_id, assignment_id)
    return None


@router.patch("/teacher/students/{assignment_id}", response_model=TeacherStudentRead)
def patch_teacher_student_display_name(
    assignment_id: int,
    payload: TeacherStudentDisplayNameUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_teacher_student_display_name(db, user, assignment_id, payload)


@router.get("/admin/course-requests", response_model=list[CourseRequestRead])
def get_admin_course_requests(
    status_filter: str | None = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_course_requests(db, status_filter=status_filter)


@router.get("/admin/teacher-applications", response_model=list[TeacherApplicationRead])
def get_admin_teacher_applications(
    status_filter: str | None = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_teacher_applications(db, status_filter=status_filter)


@router.delete("/admin/teacher-applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_teacher_application(
    application_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    delete_teacher_application(db, application_id)
    return None


@router.delete("/admin/course-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_course_request(
    request_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    delete_course_request(db, request_id)
    return None


@router.post("/admin/course-requests/{request_id}/schedule", response_model=CourseRequestRead)
def post_admin_schedule_lesson(
    request_id: int,
    payload: ScheduleLessonCreate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return schedule_lesson_for_request(db, admin, request_id, payload)


@router.get("/courses", response_model=list[CourseRead])
def get_courses(db: Session = Depends(get_db)):
    return list_courses(db)


@router.get("/courses/{slug}", response_model=CourseRead)
def get_course(slug: str, db: Session = Depends(get_db)):
    course = get_course_by_slug(db, slug)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course
