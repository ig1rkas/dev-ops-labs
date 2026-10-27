from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseRequest(Base):
    __tablename__ = "course_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Public visitors can leave a request without creating an account. When a
    # student is logged in, keep the account link as well.
    student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    # Optional direct target selected on the public teacher card.  Legacy
    # subject-only requests keep this nullable and are routed by the admin.
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), index=True, nullable=True)
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="new")
    contact_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    contact_method: Mapped[str | None] = mapped_column(String(24), nullable=True)
    contact_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("User")
    subject = relationship("Subject")
    teacher = relationship("Teacher")
    chat = relationship("Chat")


class TeacherStudentAssignment(Base):
    __tablename__ = "teacher_student_assignments"
    __table_args__ = (UniqueConstraint("teacher_id", "student_id", "subject_id", name="uq_teacher_student_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")
    # A teacher may use a private display name for this student. It belongs
    # to the assignment, so other teachers and the student's account keep the
    # original name unchanged.
    teacher_display_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    teacher = relationship("Teacher")
    teacher_user = relationship("User", foreign_keys=[teacher_user_id])
    student = relationship("User", foreign_keys=[student_id])
    subject = relationship("Subject")
    lessons = relationship("Lesson", back_populates="assignment", cascade="all, delete-orphan")
    homework = relationship("HomeworkItem", back_populates="assignment", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("teacher_student_assignments.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    topic: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(32), index=True, default="online")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment = relationship("TeacherStudentAssignment", back_populates="lessons")
    teacher = relationship("Teacher")
    teacher_user = relationship("User", foreign_keys=[teacher_user_id])
    student = relationship("User", foreign_keys=[student_id])
    subject = relationship("Subject")


class HomeworkItem(Base):
    __tablename__ = "homework_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("teacher_student_assignments.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="assigned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment = relationship("TeacherStudentAssignment", back_populates="homework")
    teacher = relationship("Teacher")
    teacher_user = relationship("User", foreign_keys=[teacher_user_id])
    student = relationship("User", foreign_keys=[student_id])
    subject = relationship("Subject")
