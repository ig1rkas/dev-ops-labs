from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import Chat, ChatMessage, ChatParticipant
from app.models.learning import TeacherStudentAssignment
from app.models.user import User

SUPPORT_TITLE = "Поддержка idioma"


def _chat_with_users(db: Session, kind: str, user_ids: set[int]) -> Chat | None:
    candidate_ids = db.scalars(select(ChatParticipant.chat_id).where(ChatParticipant.user_id.in_(user_ids))).all()
    for chat_id in set(candidate_ids):
        chat = db.execute(
            select(Chat)
            .options(joinedload(Chat.participants).joinedload(ChatParticipant.user))
            .where(Chat.id == chat_id, Chat.kind == kind)
        ).unique().scalars().first()
        if chat is None:
            continue
        participant_ids = {participant.user_id for participant in chat.participants}
        if user_ids.issubset(participant_ids):
            return chat
    return None


def _add_participant_if_missing(db: Session, chat: Chat, user_id: int) -> None:
    exists = db.scalar(
        select(ChatParticipant).where(
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.user_id == user_id,
        )
    )
    if exists is None:
        db.add(ChatParticipant(chat_id=chat.id, user_id=user_id))


def _create_chat(db: Session, title: str, kind: str, user_ids: list[int], greeting_sender_id: int | None = None, greeting: str | None = None) -> Chat:
    chat = Chat(title=title, kind=kind)
    db.add(chat)
    db.flush()
    for user_id in dict.fromkeys(user_ids):
        db.add(ChatParticipant(chat_id=chat.id, user_id=user_id))
    if greeting_sender_id and greeting:
        db.add(ChatMessage(chat_id=chat.id, sender_id=greeting_sender_id, body=greeting))
    db.commit()
    db.refresh(chat)
    return chat


def ensure_support_chat(db: Session, user: User) -> Chat | None:
    if user.role == "admin":
        return None

    admins = list(db.scalars(select(User).where(User.role == "admin").order_by(User.id)))
    admin_ids = [admin.id for admin in admins]
    chat = _chat_with_users(db, "support", {user.id})
    if chat is None:
        title = f"{SUPPORT_TITLE}: {user.full_name}"
        greeting_sender_id = admin_ids[0] if admin_ids else user.id
        chat = _create_chat(
            db,
            title=title,
            kind="support",
            user_ids=[user.id, *admin_ids],
            greeting_sender_id=greeting_sender_id,
            greeting="Здравствуйте! Это поддержка idioma. Напишите ваш вопрос, мы поможем.",
        )
    else:
        for admin_id in admin_ids:
            _add_participant_if_missing(db, chat, admin_id)
        db.commit()
    return chat


def ensure_direct_chat(db: Session, first: User, second: User) -> Chat:
    existing = _chat_with_users(db, "direct", {first.id, second.id})
    if existing is not None:
        return existing

    return _create_chat(
        db,
        title=f"{first.full_name} и {second.full_name}",
        kind="direct",
        user_ids=[first.id, second.id],
    )


def ensure_default_chats(db: Session, user: User) -> None:
    if user.role == "admin":
        users = list(db.scalars(select(User).where(User.role != "admin").order_by(User.id)))
        for target in users:
            ensure_support_chat(db, target)
        return

    ensure_support_chat(db, user)

    if user.role == "student":
        teachers = list(
            db.scalars(
                select(User)
                .join(TeacherStudentAssignment, TeacherStudentAssignment.teacher_user_id == User.id)
                .where(TeacherStudentAssignment.student_id == user.id, TeacherStudentAssignment.status == "active")
                .order_by(User.full_name)
            )
        )
        for teacher in teachers:
            ensure_direct_chat(db, user, teacher)
    elif user.role == "teacher":
        students = list(
            db.scalars(
                select(User)
                .join(TeacherStudentAssignment, TeacherStudentAssignment.student_id == User.id)
                .where(TeacherStudentAssignment.teacher_user_id == user.id, TeacherStudentAssignment.status == "active")
                .order_by(User.full_name)
            )
        )
        for student in students:
            ensure_direct_chat(db, user, student)


def _direct_chat_is_assigned(db: Session, chat: Chat, user: User) -> bool:
    participant_ids = {participant.user_id for participant in chat.participants}
    peer_ids = participant_ids - {user.id}
    if len(peer_ids) != 1:
        return False
    peer_id = next(iter(peer_ids))

    if user.role == "teacher":
        return db.scalar(
            select(TeacherStudentAssignment.id).where(
                TeacherStudentAssignment.teacher_user_id == user.id,
                TeacherStudentAssignment.student_id == peer_id,
                TeacherStudentAssignment.status == "active",
            )
        ) is not None

    if user.role == "student":
        return db.scalar(
            select(TeacherStudentAssignment.id).where(
                TeacherStudentAssignment.student_id == user.id,
                TeacherStudentAssignment.teacher_user_id == peer_id,
                TeacherStudentAssignment.status == "active",
            )
        ) is not None

    return False


def _chat_is_visible_for_user(db: Session, chat: Chat, user: User) -> bool:
    if user.role == "admin":
        return chat.kind == "support"

    participant_ids = {participant.user_id for participant in chat.participants}
    if user.id not in participant_ids:
        return False
    if chat.kind == "support":
        return True
    if chat.kind == "direct":
        return _direct_chat_is_assigned(db, chat, user)
    return False


def _authorize_chat(db: Session, chat: Chat, user: User) -> None:
    if user.role == "admin":
        return
    if not _chat_is_visible_for_user(db, chat, user):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому чату")


def chat_to_read(db: Session, chat: Chat, current_user: User) -> dict:
    participants = [participant.user for participant in chat.participants if participant.user is not None]
    peers = [participant for participant in participants if participant.id != current_user.id]
    if chat.kind == "support" and current_user.role != "admin":
        title = SUPPORT_TITLE
    else:
        title = ", ".join(peer.full_name for peer in peers) or chat.title

    last_message = db.scalar(select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()))
    return {
        "id": chat.id,
        "title": title,
        "kind": chat.kind,
        "peer_names": [peer.full_name for peer in peers],
        "last_message": last_message.body if last_message else "",
        "updated_at": last_message.created_at if last_message else chat.updated_at,
    }


def list_chats(db: Session, user: User) -> list[dict]:
    ensure_default_chats(db, user)
    stmt = select(Chat).options(joinedload(Chat.participants).joinedload(ChatParticipant.user))
    if user.role != "admin":
        stmt = stmt.join(ChatParticipant).where(ChatParticipant.user_id == user.id)
    else:
        stmt = stmt.where(Chat.kind == "support")
    chats = db.scalars(stmt.order_by(Chat.updated_at.desc(), Chat.id.desc())).unique().all()
    chats = [chat for chat in chats if _chat_is_visible_for_user(db, chat, user)]
    return [chat_to_read(db, chat, user) for chat in chats]


def get_chat_detail(db: Session, user: User, chat_id: int) -> dict:
    ensure_default_chats(db, user)
    chat = db.execute(
        select(Chat)
        .options(joinedload(Chat.participants).joinedload(ChatParticipant.user))
        .where(Chat.id == chat_id)
    ).unique().scalars().first()
    if chat is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    _authorize_chat(db, chat, user)
    messages = db.scalars(
        select(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .where(ChatMessage.chat_id == chat.id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()
    return {
        "chat": chat_to_read(db, chat, user),
        "messages": [
            {
                "id": message.id,
                "chat_id": message.chat_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender.full_name if message.sender else "idioma",
                "sender_role": message.sender.role if message.sender else "support",
                "body": message.body,
                "created_at": message.created_at,
                "is_mine": message.sender_id == user.id,
            }
            for message in messages
        ],
    }


def send_message(db: Session, user: User, chat_id: int, body: str) -> dict:
    chat = db.execute(
        select(Chat)
        .options(joinedload(Chat.participants).joinedload(ChatParticipant.user))
        .where(Chat.id == chat_id)
    ).unique().scalars().first()
    if chat is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    _authorize_chat(db, chat, user)
    clean_body = body.strip()
    if not clean_body:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Сообщение не может быть пустым")
    message = ChatMessage(chat_id=chat.id, sender_id=user.id, body=clean_body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return get_chat_detail(db, user, chat.id)


