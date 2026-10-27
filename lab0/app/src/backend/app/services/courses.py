from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course

DEFAULT_COURSES = [
    {
        "slug": "matematika-ege",
        "title": "Математика ЕГЭ",
        "category": "ЕГЭ и ОГЭ",
        "description": "Профильная математика: теория, пробники, разбор второй части и стратегия экзамена.",
        "price_month": 2490,
        "rating": 4.9,
        "lessons_count": 32,
        "accent_color": "#f04a23",
    },
    {
        "slug": "informatika-oge",
        "title": "Информатика ОГЭ",
        "category": "ЕГЭ и ОГЭ",
        "description": "Кодинг, алгоритмы и уверенная подготовка к заданиям ОГЭ.",
        "price_month": 2190,
        "rating": 4.8,
        "lessons_count": 24,
        "accent_color": "#8c6cff",
    },
    {
        "slug": "english-ielts",
        "title": "Английский IELTS",
        "category": "Международные экзамены",
        "description": "Speaking, Writing, Reading и Listening с персональной обратной связью.",
        "price_month": 2990,
        "rating": 4.9,
        "lessons_count": 28,
        "accent_color": "#3985ff",
    },
    {
        "slug": "unity-game-dev",
        "title": "Разработка игр на Unity",
        "category": "Программирование и IT",
        "description": "Практический курс по созданию игр, C# и проектному мышлению.",
        "price_month": 3490,
        "rating": 4.9,
        "lessons_count": 30,
        "accent_color": "#36b36b",
    },
]


def seed_courses(db: Session) -> None:
    existing_count = db.scalar(select(Course).limit(1))
    if existing_count is not None:
        return

    db.add_all(Course(**course) for course in DEFAULT_COURSES)
    db.commit()


def list_courses(db: Session) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.id)))


def get_course_by_slug(db: Session, slug: str) -> Course | None:
    return db.scalar(select(Course).where(Course.slug == slug))
