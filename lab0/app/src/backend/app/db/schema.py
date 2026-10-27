from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_user_telegram_columns(engine: Engine) -> None:
    """Apply the small in-place migration needed by existing installations.

    The project intentionally does not depend on Alembic yet, while Docker
    keeps an existing PostgreSQL volume between rebuilds.  ``create_all`` does
    not add columns to an existing table, so keep this migration explicit and
    idempotent.
    """

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assignment_columns = {
        column["name"] for column in inspect(engine).get_columns("teacher_student_assignments")
    }
    teacher_columns = {column["name"] for column in inspect(engine).get_columns("teachers")}
    subject_columns = {column["name"] for column in inspect(engine).get_columns("subjects")}
    course_request_columns = {column["name"] for column in inspect(engine).get_columns("course_requests")}
    telegram_message_columns = {column["name"] for column in inspect(engine).get_columns("telegram_messages")}
    with engine.begin() as connection:
        if "has_photo" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN has_photo BOOLEAN"))
        if "photo_file_id" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN photo_file_id VARCHAR(255)"))
        if "has_document" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN has_document BOOLEAN"))
        if "document_file_id" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN document_file_id VARCHAR(255)"))
        if "document_name" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN document_name VARCHAR(255)"))
        if "document_mime_type" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN document_mime_type VARCHAR(255)"))
        if "reactions_json" not in telegram_message_columns:
            connection.execute(text("ALTER TABLE telegram_messages ADD COLUMN reactions_json TEXT"))
        if "telegram_user_id" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN telegram_user_id BIGINT"))
        if "telegram_username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN telegram_username VARCHAR(180)"))
        if "teacher_display_name" not in assignment_columns:
            connection.execute(
                text(
                    "ALTER TABLE teacher_student_assignments "
                    "ADD COLUMN teacher_display_name VARCHAR(140)"
                )
            )
        if "account_email" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN account_email VARCHAR(255)"))
        if "account_disabled" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN account_disabled BOOLEAN NOT NULL DEFAULT FALSE"))
        if "lesson_price" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN lesson_price INTEGER NOT NULL DEFAULT 1500"))
        if "avatar_url" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN avatar_url TEXT"))
        if "calendar_url" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN calendar_url TEXT"))
        if "sort_order" not in teacher_columns:
            connection.execute(text("ALTER TABLE teachers ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))
            connection.execute(text("UPDATE teachers SET sort_order = id"))
        if "is_active" not in subject_columns:
            connection.execute(text("ALTER TABLE subjects ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        if "teacher_id" not in course_request_columns:
            connection.execute(text("ALTER TABLE course_requests ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_course_requests_teacher_id ON course_requests (teacher_id)"))
        if "contact_name" not in course_request_columns:
            connection.execute(text("ALTER TABLE course_requests ADD COLUMN contact_name VARCHAR(140)"))
        if "contact_method" not in course_request_columns:
            connection.execute(text("ALTER TABLE course_requests ADD COLUMN contact_method VARCHAR(24)"))
        if "contact_value" not in course_request_columns:
            connection.execute(text("ALTER TABLE course_requests ADD COLUMN contact_value VARCHAR(255)"))
        # PostgreSQL Docker volumes created by older versions required an
        # account and support chat for every request. Public requests make
        # those links optional. Fresh SQLite test databases already use the
        # nullable model definition above.
        if engine.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE course_requests ALTER COLUMN student_id DROP NOT NULL"))
            connection.execute(text("ALTER TABLE course_requests ALTER COLUMN chat_id DROP NOT NULL"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_teachers_account_email ON teachers (account_email)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_teachers_sort_order ON teachers (sort_order)")
        )

        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_user_id ON users (telegram_user_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_telegram_username ON users (telegram_username)")
        )
