from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Subject, Teacher, TeacherSubject, User
from app.services.auth import get_user_by_email, hash_password
from app.services.catalog import seed_catalog
from app.services.courses import seed_courses


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add a teacher profile and teacher login account to the database.",
    )
    parser.add_argument("--name", help="Teacher full name")
    parser.add_argument("--email", help="Teacher login email")
    parser.add_argument("--password", help="Teacher login password")
    parser.add_argument("--role", help="Teacher role/title shown on the website")
    parser.add_argument("--description", help="Short teacher bio/description")
    parser.add_argument("--subject-slug", help="Subject slug from the subjects table")
    parser.add_argument("--initials", help="Teacher initials, for example DP")
    parser.add_argument("--rating", default="4.9", help="Teacher rating, default: 4.9")
    parser.add_argument("--list-subjects", action="store_true", help="Print available subjects and exit")
    parser.add_argument("--dry-run", action="store_true", help="Validate input and show what would be created")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    return parser


def normalize_initials(name: str) -> str:
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "TT"
    initials = "".join(part[0] for part in parts[:4]).upper()
    return initials[:8] or name[:2].upper()


def prompt_value(label: str, current: str | None = None, default: str | None = None, secret: bool = False) -> str:
    parts = [label]
    if current:
        parts.append(f"[{current}]")
    elif default is not None:
        parts.append(f"[{default}]")
    prompt = " ".join(parts) + ": "
    raw = input(prompt).strip() if not secret else __import__("getpass").getpass(prompt).strip()
    if raw:
        return raw
    if current:
        return current
    if default is not None:
        return default
    return ""


def parse_rating(raw: str) -> Decimal:
    try:
        rating = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Rating must be a valid number, for example 4.9") from exc

    if rating < Decimal("0.0") or rating > Decimal("9.9"):
        raise ValueError("Rating must be between 0.0 and 9.9")
    return rating.quantize(Decimal("0.1"))


def print_subjects(db) -> None:
    subjects = list(db.scalars(select(Subject).order_by(Subject.title)).all())
    if not subjects:
        print("No subjects found in the database.")
        return

    print("Available subjects:")
    for subject in subjects:
        exam_type = subject.exam_type or "-"
        print(f"- {subject.slug}: {subject.title} | category={subject.category} | exam_type={exam_type}")


def build_payload(args: argparse.Namespace, db) -> dict[str, object]:
    if args.list_subjects:
        return {}

    if not args.name:
        args.name = prompt_value("Teacher name")
    if not args.email:
        args.email = prompt_value("Teacher login email")
    if not args.password:
        args.password = prompt_value("Teacher login password", secret=True)
    if not args.role:
        args.role = prompt_value("Teacher public role")
    if not args.description:
        args.description = prompt_value("Teacher public description")
    if not args.subject_slug:
        print_subjects(db)
        args.subject_slug = prompt_value("Subject slug")
    if not args.initials:
        args.initials = prompt_value("Initials", default=normalize_initials(args.name))
    if not args.rating:
        args.rating = prompt_value("Rating", default="4.9")

    missing = [
        label
        for label, value in {
            "name": args.name,
            "email": args.email,
            "password": args.password,
            "role": args.role,
            "description": args.description,
            "subject_slug": args.subject_slug,
            "initials": args.initials,
            "rating": args.rating,
        }.items()
        if not str(value).strip()
    ]
    if missing:
        raise ValueError("Missing required values: " + ", ".join(missing))
    if len(str(args.password)) < 6:
        raise ValueError("Password must be at least 6 characters long")

    rating = parse_rating(str(args.rating))

    return {
        "name": str(args.name).strip(),
        "email": str(args.email).strip().lower(),
        "password": str(args.password),
        "role": str(args.role).strip(),
        "description": str(args.description).strip(),
        "subject_slug": str(args.subject_slug).strip(),
        "initials": str(args.initials).strip().upper()[:8],
        "rating": rating,
    }


def print_payload(payload: dict[str, object], subject: Subject, dry_run: bool) -> None:
    print()
    print("Teacher profile:")
    print(f"- name: {payload['name']}")
    print(f"- public role: {payload['role']}")
    print(f"- description: {payload['description']}")
    print(f"- subject: {subject.title} ({subject.slug})")
    print(f"- initials: {payload['initials']}")
    print(f"- rating: {payload['rating']}")
    print()
    print("Teacher account:")
    print(f"- email: {payload['email']}")
    print("- password: will be stored as a hash")
    if dry_run:
        print()
        print("Dry run complete. Nothing was written to the database.")


def confirm_creation(payload: dict[str, object], subject: Subject) -> bool:
    print_payload(payload, subject, False)
    answer = input("\nCreate teacher profile and account? [y/N]: ").strip().lower()
    return answer in {"y", "yes", "д", "да"}


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

        payload = build_payload(args, db)
        subject = db.scalar(select(Subject).where(Subject.slug == payload["subject_slug"]))
        if subject is None:
            print(f"Subject with slug '{payload['subject_slug']}' was not found.\n")
            print_subjects(db)
            return 1

        duplicate_teacher = db.scalar(
            select(Teacher).where(
                Teacher.name == payload["name"],
                Teacher.subject_id == subject.id,
            )
        )
        if duplicate_teacher is not None:
            print(
                f"Teacher '{duplicate_teacher.name}' for subject '{subject.slug}' already exists "
                f"(id={duplicate_teacher.id})."
            )
            return 1

        duplicate_user = get_user_by_email(db, str(payload["email"]))
        if duplicate_user is not None:
            print(f"User with email '{payload['email']}' already exists (id={duplicate_user.id}).")
            return 1

        if args.dry_run:
            print_payload(payload, subject, True)
            return 0
        if not args.yes and not confirm_creation(payload, subject):
            return 0

        user = User(
            email=payload["email"],
            full_name=payload["name"],
            role="teacher",
            password_hash=hash_password(str(payload["password"])),
        )
        teacher = Teacher(
            name=payload["name"],
            role=payload["role"],
            description=payload["description"],
            rating=payload["rating"],
            initials=payload["initials"],
            subject_id=subject.id,
            account_email=user.email,
        )
        db.add_all([user, teacher])
        db.flush()
        db.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))
        db.commit()
        db.refresh(user)
        db.refresh(teacher)

        print()
        print(
            "Teacher created successfully: "
            f"teacher_id={teacher.id}, user_id={user.id}, email={user.email}, subject={subject.slug}"
        )
        return 0
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())




