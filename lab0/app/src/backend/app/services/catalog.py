from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject

DEFAULT_SUBJECTS = [
    {
        "slug": "matematika-ege",
        "title": "Математика ЕГЭ",
        "category": "exams",
        "exam_type": "ege",
        "description": "Профильный уровень, теория, пробники и разбор второй части.",
        "price_month": 2490,
        "icon": "sum",
        "tint": "peach",
    },
    {
        "slug": "informatika-oge",
        "title": "Информатика ОГЭ",
        "category": "exams",
        "exam_type": "oge",
        "description": "Кодинг, алгоритмы и уверенная подготовка к заданиям ОГЭ.",
        "price_month": 2190,
        "icon": "code",
        "tint": "sky",
    },
    {
        "slug": "russkiy-ege",
        "title": "Русский язык ЕГЭ",
        "category": "exams",
        "exam_type": "ege",
        "description": "Сочинение, тестовая часть, критерии и практика по вариантам.",
        "price_month": 2390,
        "icon": "language",
        "tint": "violet",
    },
    {
        "slug": "obschestvo-ege",
        "title": "Обществознание ЕГЭ",
        "category": "exams",
        "exam_type": "ege",
        "description": "Теория блоками, практика и работа с форматом экзамена.",
        "price_month": 2490,
        "icon": "history",
        "tint": "peach",
    },
    {
        "slug": "fizika-school",
        "title": "Физика 5-11 классы",
        "category": "school",
        "exam_type": None,
        "description": "Формулы, задачи и понятные связки между темами.",
        "price_month": 1990,
        "icon": "physics",
        "tint": "sky",
    },
    {
        "slug": "biologiya-school",
        "title": "Биология",
        "category": "school",
        "exam_type": None,
        "description": "Системная подготовка, термины, схемы и задания.",
        "price_month": 2390,
        "icon": "biology",
        "tint": "mint",
    },
    {
        "slug": "english-ielts",
        "title": "Английский язык IELTS",
        "category": "international",
        "exam_type": None,
        "description": "Speaking, Writing, Reading и Listening с персональной обратной связью.",
        "price_month": 2990,
        "icon": "ielts",
        "tint": "mint",
    },
    {
        "slug": "toefl",
        "title": "TOEFL",
        "category": "international",
        "exam_type": None,
        "description": "Подготовка к академическому английскому и формату TOEFL.",
        "price_month": 2990,
        "icon": "toefl",
        "tint": "sky",
    },
    {
        "slug": "hsk",
        "title": "HSK",
        "category": "international",
        "exam_type": None,
        "description": "Китайский язык, лексика, грамматика и тренировочные тесты.",
        "price_month": 2490,
        "icon": "hsk",
        "tint": "rose",
    },
    {
        "slug": "jlpt",
        "title": "JLPT",
        "category": "international",
        "exam_type": None,
        "description": "Японский язык и подготовка к уровням международного экзамена.",
        "price_month": 2490,
        "icon": "jlpt",
        "tint": "peach",
    },
    {
        "slug": "dele",
        "title": "DELE",
        "category": "international",
        "exam_type": None,
        "description": "Испанский язык и тренировка письменной и устной части.",
        "price_month": 2490,
        "icon": "dele",
        "tint": "rose",
    },
    {
        "slug": "python",
        "title": "Python",
        "category": "programming",
        "exam_type": None,
        "description": "Разработка на Python с нуля до уверенного проектного уровня.",
        "price_month": 2590,
        "icon": "python",
        "tint": "sky",
    },
    {
        "slug": "web-development",
        "title": "Веб-разработка",
        "category": "programming",
        "exam_type": None,
        "description": "Сайты и веб-приложения на HTML, CSS и JavaScript.",
        "price_month": 2690,
        "icon": "web",
        "tint": "violet",
    },
    {
        "slug": "unity-game-dev",
        "title": "Разработка игр на Unity",
        "category": "programming",
        "exam_type": None,
        "description": "2D/3D игры, логика геймплея и проектное мышление.",
        "price_month": 3490,
        "icon": "game",
        "tint": "rose",
    },
    {
        "slug": "algorithms",
        "title": "Алгоритмы и структуры данных",
        "category": "programming",
        "exam_type": None,
        "description": "Олимпиады, технические интервью и сильная алгоритмическая база.",
        "price_month": 2490,
        "icon": "network",
        "tint": "mint",
    },
    {
        "slug": "fizika-ege",
        "title": "Физика ЕГЭ",
        "category": "exams",
        "exam_type": "ege",
        "description": "Механика, электродинамика и решение задач второй части ЕГЭ.",
        "price_month": 2590,
        "icon": "physics",
        "tint": "sky",
    },
    {
        "slug": "himia-ege",
        "title": "Химия ЕГЭ",
        "category": "exams",
        "exam_type": "ege",
        "description": "Органическая и неорганическая химия с системной практикой.",
        "price_month": 2490,
        "icon": "chemistry",
        "tint": "mint",
    },
    {
        "slug": "russkiy-school",
        "title": "Русский язык 5-11 классы",
        "category": "school",
        "exam_type": None,
        "description": "Грамматика, орфография и развитие письменной речи.",
        "price_month": 1990,
        "icon": "language",
        "tint": "violet",
    },
    {
        "slug": "javascript",
        "title": "JavaScript",
        "category": "programming",
        "exam_type": None,
        "description": "Современный JavaScript, интерфейсы и практика веб-разработки.",
        "price_month": 2790,
        "icon": "web",
        "tint": "sky",
    },
    {
        "slug": "german",
        "title": "Немецкий язык",
        "category": "languages",
        "exam_type": None,
        "description": "Немецкий для учёбы, работы и уверенного общения.",
        "price_month": 2490,
        "icon": "language",
        "tint": "rose",
    },
    {
        "slug": "history-school",
        "title": "История России",
        "category": "school",
        "exam_type": None,
        "description": "Понятная хронология, карты и практика экзаменационных заданий.",
        "price_month": 2190,
        "icon": "history",
        "tint": "peach",
    },
]

DEFAULT_TEACHERS = [
    {
        "name": "Алексей В.",
        "role": "Преподаватель математики",
        "description": "Готовлю к ЕГЭ больше 10 лет. Ученики стабильно набирают 80+ баллов.",
        "rating": 4.9,
        "initials": "АВ",
        "subject_slug": "matematika-ege",
    },
    {
        "name": "Мария С.",
        "role": "Преподаватель английского",
        "description": "Сдала IELTS на 8.5 и помогаю ученикам уверенно достигать своих целей.",
        "rating": 5.0,
        "initials": "МС",
        "subject_slug": "english-ielts",
    },
    {
        "name": "Игорь К.",
        "role": "Преподаватель IT",
        "description": "Учу программировать на практике и готовлю к реальным задачам индустрии.",
        "rating": 4.9,
        "initials": "ИК",
        "subject_slug": "python",
    },
    {
        "name": "Ирина Волкова",
        "role": "Русский язык",
        "description": "Разбираем сочинения, тестовую часть и ловушки экзамена без паники.",
        "rating": 5.0,
        "initials": "ИВ",
        "subject_slug": "russkiy-ege",
    },
    {
        "name": "Дмитрий Ковалёв",
        "role": "Английский язык",
        "description": "Делаем упор на разговорную практику, грамматику и уверенность на экзамене.",
        "rating": 4.8,
        "initials": "ДК",
        "subject_slug": "toefl",
    },
    {
        "name": "Екатерина Лебедева",
        "role": "Биология",
        "description": "Помогаю разложить сложные темы по схемам и уверенно решать задания.",
        "rating": 4.9,
        "initials": "ЕЛ",
        "subject_slug": "biologiya-school",
    },
]


def seed_catalog(db: Session) -> None:
    existing_slugs = {subject.slug for subject in db.scalars(select(Subject)).all()}
    missing_subjects = [subject for subject in DEFAULT_SUBJECTS if subject["slug"] not in existing_slugs]
    if missing_subjects:
        db.add_all(Subject(**subject) for subject in missing_subjects)
        db.commit()

    if db.scalar(select(Teacher).limit(1)) is not None:
        return

    subjects_by_slug = {subject.slug: subject for subject in db.scalars(select(Subject)).all()}
    teachers = []
    for teacher in DEFAULT_TEACHERS:
        subject = subjects_by_slug.get(teacher["subject_slug"])
        if subject is None:
            continue
        data = {key: value for key, value in teacher.items() if key != "subject_slug"}
        teachers.append(Teacher(**data, subject_id=subject.id, sort_order=len(teachers) + 1))

    db.add_all(teachers)
    db.commit()


def ensure_teacher_subject_links(db: Session) -> None:
    """Backfill the many-to-many subject link for legacy teacher rows."""
    changed = False
    for teacher in db.scalars(select(Teacher)).all():
        exists = db.scalar(
            select(TeacherSubject.id).where(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == teacher.subject_id,
            )
        )
        if exists is None:
            db.add(TeacherSubject(teacher_id=teacher.id, subject_id=teacher.subject_id))
            changed = True
    if changed:
        db.commit()


def list_subjects(db: Session, category: str | None = None, exam_type: str | None = None, q: str | None = None) -> list[Subject]:
    stmt = select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.id)
    if category and category != "all":
        stmt = stmt.where(Subject.category == category)
    if exam_type and exam_type != "all":
        stmt = stmt.where(Subject.exam_type == exam_type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Subject.title.ilike(like), Subject.description.ilike(like)))
    return list(db.scalars(stmt))


def list_teachers(db: Session, category: str | None = None, subject_slug: str | None = None, q: str | None = None) -> list[Teacher]:
    stmt = (
        select(Teacher)
        .options(joinedload(Teacher.subject), joinedload(Teacher.subject_assignments).joinedload(TeacherSubject.subject))
        .join(Teacher.subject)
        .where(Teacher.account_disabled.is_(False))
        .order_by(Teacher.sort_order, Teacher.id)
    )
    if category and category != "all":
        stmt = stmt.where(
            (Subject.category == category)
            | Teacher.id.in_(select(TeacherSubject.teacher_id).join(Subject).where(Subject.category == category))
        )
    if subject_slug:
        stmt = stmt.where(
            (Subject.slug == subject_slug)
            | Teacher.id.in_(select(TeacherSubject.teacher_id).join(Subject).where(Subject.slug == subject_slug))
        )
    if q:
        like = f"%{q.strip()}%"
        linked_subject_match = Teacher.id.in_(
            select(TeacherSubject.teacher_id)
            .join(Subject, TeacherSubject.subject_id == Subject.id)
            .where(
                Subject.is_active.is_(True),
                or_(Subject.title.ilike(like), Subject.slug.ilike(like), Subject.description.ilike(like)),
            )
        )
        stmt = stmt.where(
            or_(
                Teacher.name.ilike(like),
                Teacher.role.ilike(like),
                Teacher.description.ilike(like),
                Subject.title.ilike(like),
                linked_subject_match,
            )
        )
    return list(db.scalars(stmt).unique())


def teacher_to_read(teacher: Teacher) -> dict:
    subject_items = []
    seen = set()
    for subject in [teacher.subject, *(assignment.subject for assignment in teacher.subject_assignments or [])]:
        if subject is None or subject.id in seen:
            continue
        seen.add(subject.id)
        subject_items.append({
            "id": subject.id,
            "slug": subject.slug,
            "title": subject.title,
            "category": subject.category,
            "exam_type": subject.exam_type,
            "icon": subject.icon,
        })
    categories = list(dict.fromkeys(subject["category"] for subject in subject_items))
    return {
        "id": teacher.id,
        "name": teacher.name,
        "role": teacher.role,
        "description": teacher.description,
        "rating": teacher.rating,
        "initials": teacher.initials,
        "subject_id": teacher.subject_id,
        "subject_title": teacher.subject.title,
        "subject_slug": teacher.subject.slug,
        "category": teacher.subject.category,
        "categories": categories,
        "subjects": subject_items,
        "lesson_price": teacher.lesson_price,
        "avatar_url": teacher.avatar_url,
        "created_at": teacher.created_at,
    }
