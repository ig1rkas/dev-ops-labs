from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Subject, Teacher, TeacherSubject, User
from app.services.catalog import seed_catalog
from app.services.courses import seed_courses
from app.services.teacher_subjects import add_subject_to_teacher, find_teacher, get_subject


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assign an additional subject to a teacher.")
    parser.add_argument("--teacher-id", type=int, help="Teacher profile id from teachers table")
    parser.add_argument("--teacher-email", help="Teacher login email from users table")
    parser.add_argument("--teacher-name", help="Teacher public name from teachers table")
    parser.add_argument("--subject-slug", help="Subject slug from subjects table")
    parser.add_argument("--list-teachers", action="store_true", help="Print available teacher profiles and exit")
    parser.add_argument("--list-subjects", action="store_true", help="Print available subjects and exit")
    parser.add_argument("--dry-run", action="store_true", help="Validate input without writing to the database")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    return parser


def print_subjects(db) -> None:
    subjects = list(db.scalars(select(Subject).order_by(Subject.title)).all())
    print("Available subjects:")
    for subject in subjects:
        exam_type = subject.exam_type or "-"
        print(f"- {subject.slug}: {subject.title} | category={subject.category} | exam_type={exam_type}")


def print_teachers(db) -> None:
    teachers = list(db.scalars(select(Teacher).order_by(Teacher.name)).all())
    print("Available teachers:")
    for teacher in teachers:
        print(f"- id={teacher.id}: {teacher.name} | role={teacher.role}")


def prompt_value(label: str) -> str:
    return input(f"{label}: ").strip()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_courses(db)
        seed_catalog(db)

        if args.list_subjects:
            print_subjects(db)
            return 0
        if args.list_teachers:
            print_teachers(db)
            return 0

        if not args.teacher_id and not args.teacher_email and not args.teacher_name:
            print_teachers(db)
            args.teacher_email = prompt_value("Teacher email")
        if not args.subject_slug:
            print_subjects(db)
            args.subject_slug = prompt_value("Subject slug")

        teacher = find_teacher(db, args.teacher_id, args.teacher_email, args.teacher_name)
        if teacher is None:
            print("Teacher was not found. Use --list-teachers to check available profiles.")
            return 1

        subject = get_subject(db, args.subject_slug)
        if subject is None:
            print(f"Subject with slug '{args.subject_slug}' was not found.")
            print_subjects(db)
            return 1

        duplicate = db.scalar(
            select(TeacherSubject).where(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == subject.id,
            )
        )
        if duplicate is not None:
            print(f"Teacher '{teacher.name}' already has subject '{subject.slug}'.")
            return 0

        print()
        print("Assignment:")
        print(f"- teacher: {teacher.name} (id={teacher.id})")
        print(f"- subject: {subject.title} ({subject.slug})")

        if args.dry_run:
            print("Dry run complete. Nothing was written to the database.")
            return 0

        if not args.yes:
            answer = input("Assign subject to teacher? [y/N]: ").strip().lower()
            if answer not in {"y", "yes", "д", "да"}:
                return 0

        _, created = add_subject_to_teacher(db, teacher, subject)
        if created:
            print(f"Subject '{subject.slug}' was assigned to teacher '{teacher.name}'.")
        else:
            print(f"Teacher '{teacher.name}' already has subject '{subject.slug}'.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
