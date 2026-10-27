import json
import time

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.learning import TeacherStudentAssignment
from app.models.telegram import TelegramChat, TelegramChatReadState, TelegramDeletedMessage, TelegramDocument, TelegramMessage, TelegramPhoto
from app.models.user import User


_reaction_refresh_at: dict[int, float] = {}


def _require_teacher_or_admin(user: User) -> None:
    from fastapi import HTTPException, status

    if user.role not in {"teacher", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram-чаты доступны только преподавателям и администратору",
        )


def _assigned_telegram_ids(db: Session, user: User) -> set[int]:
    if user.role == "admin":
        return set()
    assigned_ids = {
        value
        for value in db.scalars(
            select(User.telegram_user_id)
            .join(TeacherStudentAssignment, TeacherStudentAssignment.student_id == User.id)
            .where(
                TeacherStudentAssignment.teacher_user_id == user.id,
                TeacherStudentAssignment.status == "active",
                User.telegram_user_id.is_not(None),
            )
        ).all()
        if value is not None
    }
    system_sender_ids = {
        value
        for value in db.scalars(
            select(TelegramMessage.sender_telegram_id).where(
                TelegramMessage.direction == "outbound",
                TelegramMessage.sender_telegram_id.is_not(None),
            )
        ).all()
        if value is not None
    }
    return assigned_ids - system_sender_ids


def _chat_contact_ids(db: Session, chat: TelegramChat) -> set[int]:
    if chat.chat_type == "private" and chat.telegram_chat_id > 0:
        return {int(chat.telegram_chat_id)}
    return {
        value
        for value in db.scalars(
            select(TelegramMessage.sender_telegram_id).where(
                TelegramMessage.chat_id == chat.id,
                TelegramMessage.sender_telegram_id.is_not(None),
                TelegramMessage.direction == "inbound",
            )
        ).all()
        if value is not None
    }


def _chat_visible_for_user(db: Session, chat: TelegramChat, user: User) -> bool:
    if user.role == "admin":
        return True
    assigned_ids = _assigned_telegram_ids(db, user)
    if not assigned_ids:
        return False
    # A private Telegram dialog belongs to exactly one peer.  Message sender
    # ids are not an access-control key: outgoing messages are sent by the
    # connected account and used to make unrelated chats visible here.
    if chat.chat_type == "private":
        return chat.telegram_chat_id in assigned_ids
    return bool(_chat_contact_ids(db, chat) & assigned_ids)


def _student_name_for_chat(db: Session, chat: TelegramChat, user: User) -> str | None:
    if chat.chat_type == "private":
        student = db.scalar(
            select(User).where(
                User.role == "student",
                User.telegram_user_id == chat.telegram_chat_id,
            )
        )
    else:
        contact_ids = _chat_contact_ids(db, chat)
        if not contact_ids:
            return None
        student = db.scalar(
            select(User)
            .where(User.role == "student", User.telegram_user_id.in_(contact_ids))
            .order_by(User.id)
        )
    if student is None:
        return None
    if user.role == "teacher":
        assignment = db.scalar(
            select(TeacherStudentAssignment).where(
                TeacherStudentAssignment.teacher_user_id == user.id,
                TeacherStudentAssignment.student_id == student.id,
                TeacherStudentAssignment.status == "active",
            )
        )
        if assignment is not None and assignment.teacher_display_name:
            return assignment.teacher_display_name
    return student.full_name


def _latest_message_id(db: Session, chat_id: int) -> int | None:
    return db.scalar(select(func.max(TelegramMessage.id)).where(TelegramMessage.chat_id == chat_id))


def _read_state(db: Session, chat: TelegramChat, user: User) -> tuple[TelegramChatReadState, bool]:
    state = db.scalar(
        select(TelegramChatReadState).where(
            TelegramChatReadState.chat_id == chat.id,
            TelegramChatReadState.user_id == user.id,
        )
    )
    created = state is None
    if created:
        # Existing imported history starts as read. New inbound messages create
        # states before they are inserted, so they still appear as unread.
        state = TelegramChatReadState(
            chat_id=chat.id,
            user_id=user.id,
            last_read_message_id=_latest_message_id(db, chat.id),
        )
        db.add(state)
        db.flush()
    return state, created


def _unread_count(db: Session, chat: TelegramChat, user: User) -> int:
    state, _created = _read_state(db, chat, user)
    return int(
        db.scalar(
            select(func.count(TelegramMessage.id)).where(
                TelegramMessage.chat_id == chat.id,
                TelegramMessage.direction == "inbound",
                TelegramMessage.id > (state.last_read_message_id or 0),
            )
        )
        or 0
    )


def _mark_chat_read(db: Session, chat: TelegramChat, user: User) -> None:
    state, created = _read_state(db, chat, user)
    latest_message_id = _latest_message_id(db, chat.id)
    if created or state.last_read_message_id != latest_message_id:
        state.last_read_message_id = latest_message_id
        db.commit()


def _chat_read(db: Session, chat: TelegramChat, user: User) -> dict:
    last = db.scalar(
        select(TelegramMessage)
        .where(TelegramMessage.chat_id == chat.id)
        .order_by(TelegramMessage.created_at.desc(), TelegramMessage.id.desc())
    )
    return {
        "id": chat.id,
        "telegram_chat_id": chat.telegram_chat_id if user.role == "admin" else None,
        # Administrators need the actual Telegram peer title.  Student account
        # names are editable/imported metadata and must not replace it.  A
        # teacher may still use their private display name for an assignment.
        "title": (_student_name_for_chat(db, chat, user) if user.role == "teacher" else None) or chat.title,
        "username": chat.username if user.role == "admin" else None,
        "chat_type": chat.chat_type,
        "last_message": last.body if last else "",
        "unread_count": _unread_count(db, chat, user),
        "updated_at": last.created_at if last else chat.updated_at,
    }


def list_telegram_chats(db: Session, user: User) -> list[dict]:
    _require_teacher_or_admin(user)
    chats = db.scalars(select(TelegramChat).order_by(TelegramChat.updated_at.desc(), TelegramChat.id.desc())).all()
    result = [_chat_read(db, chat, user) for chat in chats if _chat_visible_for_user(db, chat, user)]
    db.commit()
    return result


def telegram_status(user: User) -> dict:
    _require_teacher_or_admin(user)
    from app.core.config import settings
    from app import tg

    return {
        "configured": bool(settings.telegram_bot_token),
        "polling_enabled": settings.telegram_polling_enabled,
        "running": bool(tg.bot is not None and tg._polling_task is not None and not tg._polling_task.done()),
        "mtproto_configured": bool(
            settings.telegram_mtproto_enabled
            and settings.telegram_api_id
            and (settings.telegram_api_hash or "").strip()
        ),
        "mtproto_authorized": bool(tg._mtproto_authorized),
        "mtproto_running": bool(
            tg.mtproto_client is not None
            and tg._mtproto_task is not None
            and not tg._mtproto_task.done()
        ),
        "mtproto_error": tg._mtproto_error,
    }


def _get_visible_chat(db: Session, user: User, chat_id: int) -> TelegramChat:
    from fastapi import HTTPException, status

    chat = db.get(TelegramChat, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram-чат не найден")
    if not _chat_visible_for_user(db, chat, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чат не назначен этому преподавателю")
    return chat


def get_telegram_chat_detail(db: Session, user: User, chat_id: int, *, limit: int = 200) -> dict:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    # The complete transcript is retained in PostgreSQL, but sending every
    # historical message to the browser on each real-time refresh can exhaust
    # a small VPS. The UI only needs the current conversation window.
    messages = list(reversed(db.scalars(
        select(TelegramMessage)
        .where(TelegramMessage.chat_id == chat.id)
        .order_by(TelegramMessage.id.desc())
        .limit(limit)
    ).all()))
    _mark_chat_read(db, chat, user)
    return {
        "chat": _chat_read(db, chat, user),
        "messages": [
            {
                "id": message.id,
                "telegram_message_id": message.telegram_message_id if user.role == "admin" else None,
                "sender_name": message.sender_name,
                "sender_username": message.sender_username if user.role == "admin" else None,
                "body": message.body,
                "has_photo": bool(message.has_photo),
                "has_document": bool(message.has_document),
                "document_name": message.document_name,
                "reactions": json.loads(message.reactions_json or "[]"),
                "direction": message.direction,
                "created_at": message.created_at,
                "telegram_date": message.telegram_date,
            }
            for message in messages
        ],
    }


def delete_telegram_message(db: Session, admin: User, chat_id: int, message_id: int) -> dict:
    from fastapi import HTTPException, status

    if admin.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удалять сообщения может только администратор")
    chat = db.get(TelegramChat, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    message = db.scalar(
        select(TelegramMessage).where(
            TelegramMessage.id == message_id,
            TelegramMessage.chat_id == chat.id,
        )
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")

    already_deleted = db.scalar(
        select(TelegramDeletedMessage.id).where(
            TelegramDeletedMessage.chat_id == chat.id,
            TelegramDeletedMessage.telegram_message_id == message.telegram_message_id,
        )
    )
    if already_deleted is None:
        db.add(
            TelegramDeletedMessage(
                chat_id=chat.id,
                telegram_message_id=message.telegram_message_id,
            )
        )
    db.delete(message)
    db.commit()
    return get_telegram_chat_detail(db, admin, chat.id)


async def send_telegram_photo_message(
    db: Session, user: User, chat_id: int, data: bytes, filename: str, caption: str
) -> dict:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    from app.tg import send_telegram_photo

    try:
        await send_telegram_photo(chat, data, caption, filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.expire_all()
    return get_telegram_chat_detail(db, user, chat.id)


async def send_telegram_document_message(
    db: Session, user: User, chat_id: int, data: bytes, filename: str, caption: str
) -> dict:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    from app.tg import send_telegram_document

    try:
        await send_telegram_document(chat, data, caption, filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.expire_all()
    return get_telegram_chat_detail(db, user, chat.id)


async def get_telegram_document(db: Session, user: User, chat_id: int, message_id: int) -> tuple[bytes, str, str]:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    message = db.scalar(
        select(TelegramMessage).where(
            TelegramMessage.id == message_id,
            TelegramMessage.chat_id == chat.id,
            TelegramMessage.has_document.is_(True),
        )
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    cached = db.scalar(select(TelegramDocument).where(TelegramDocument.message_id == message.id))
    if cached is None:
        from app.tg import download_telegram_document

        try:
            data = await download_telegram_document(
                int(chat.telegram_chat_id), int(message.telegram_message_id), message.document_file_id
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Файл временно недоступен") from exc
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
        db.add(TelegramDocument(message_id=message.id, data=data))
        db.commit()
    else:
        data = cached.data
    return data, message.document_mime_type or "application/octet-stream", message.document_name or "Файл"


async def get_telegram_photo(db: Session, user: User, chat_id: int, message_id: int) -> tuple[bytes, str]:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    message = db.scalar(
        select(TelegramMessage).where(
            TelegramMessage.id == message_id,
            TelegramMessage.chat_id == chat.id,
            TelegramMessage.has_photo.is_(True),
        )
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото не найдено")
    cached = db.scalar(select(TelegramPhoto).where(TelegramPhoto.message_id == message.id))
    if cached is not None:
        return cached.data, cached.mime_type

    from app.tg import download_telegram_photo

    try:
        data = await download_telegram_photo(
            int(chat.telegram_chat_id), int(message.telegram_message_id), message.photo_file_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Фото временно недоступно") from exc
    if not data or len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Фото слишком большое")
    mime_type = image_mime_type(data)
    if mime_type is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Файл не является фотографией")
    db.add(TelegramPhoto(message_id=message.id, data=data, mime_type=mime_type))
    db.commit()
    return data, mime_type


def image_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def discover_legacy_telegram_photos(
    db: Session, user: User, chat_id: int, *, limit: int = 200
) -> None:
    """Fill media metadata for old messages only once per viewed conversation."""

    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    unknown_ids = db.scalars(
        select(TelegramMessage.telegram_message_id)
        .where(
            TelegramMessage.chat_id == chat.id,
            (TelegramMessage.has_photo.is_(None) | TelegramMessage.has_document.is_(None)),
        )
        .order_by(TelegramMessage.id.desc())
        .limit(limit)
    ).all()
    if not unknown_ids:
        return
    from app.tg import telegram_media_metadata

    try:
        metadata = await telegram_media_metadata(int(chat.telegram_chat_id), list(unknown_ids))
    except Exception:
        return
    if not metadata:
        return
    for telegram_message_id, media in metadata.items():
        db.execute(
            update(TelegramMessage)
            .where(
                TelegramMessage.chat_id == chat.id,
                TelegramMessage.telegram_message_id == telegram_message_id,
            )
            .values(**media)
        )
    db.commit()


async def refresh_telegram_reactions(db: Session, user: User, chat_id: int, *, limit: int = 200) -> None:
    """Read visible-message reactions so updates are not lost during restarts."""

    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    from app import tg

    client = tg.mtproto_client
    if client is None or not tg._mtproto_authorized or not client.is_connected():
        return
    now = time.monotonic()
    if now - _reaction_refresh_at.get(chat.id, 0) < 30:
        return
    _reaction_refresh_at[chat.id] = now
    messages = db.scalars(
        select(TelegramMessage)
        .where(TelegramMessage.chat_id == chat.id)
        .order_by(TelegramMessage.id.desc())
        .limit(limit)
    ).all()
    if not messages:
        return
    try:
        entity = await client.get_input_entity(int(chat.telegram_chat_id))
        fetched = await client.get_messages(entity, ids=[message.telegram_message_id for message in messages])
    except Exception:
        return
    changed = False
    stored_by_telegram_id = {message.telegram_message_id: message for message in messages}
    for remote in fetched:
        if remote is None:
            continue
        stored = stored_by_telegram_id.get(int(remote.id))
        if stored is None:
            continue
        if getattr(remote, "reactions", None) is None and stored.reactions_json is None:
            continue
        encoded = json.dumps(tg._reaction_summary(getattr(remote, "reactions", None)), ensure_ascii=False)
        if stored.reactions_json != encoded:
            stored.reactions_json = encoded
            changed = True
    if changed:
        db.commit()


async def send_telegram_message(db: Session, user: User, chat_id: int, body: str) -> dict:
    _require_teacher_or_admin(user)
    chat = _get_visible_chat(db, user, chat_id)
    clean_body = body.strip()
    if not clean_body:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Сообщение не может быть пустым")

    from app.tg import send_telegram_text

    try:
        await send_telegram_text(chat, clean_body)
    except RuntimeError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return get_telegram_chat_detail(db, user, chat.id)
