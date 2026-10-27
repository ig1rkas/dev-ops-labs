"""Telegram integrations.

The application supports both the Bot API (including Business updates) and a
user-authorized MTProto client. MTProto sends teacher replies as the configured
Telegram account and avoids the Business Bot API's recent-contact restriction.
"""

import asyncio
import io
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.learning import TeacherStudentAssignment
from app.models.telegram import TelegramChat, TelegramChatReadState, TelegramDeletedMessage, TelegramIgnoredChat, TelegramMessage
from app.models.user import User
from app.services.auth import hash_password

try:  # aiogram remains optional for MTProto-only installations.
    from aiogram import Bot, Dispatcher
    from aiogram.types import BusinessConnection, Message
except ImportError:  # pragma: no cover - exercised only in minimal installs
    Bot = None  # type: ignore[assignment,misc]
    Dispatcher = None  # type: ignore[assignment,misc]
    BusinessConnection = Any  # type: ignore[assignment,misc]
    Message = Any  # type: ignore[assignment,misc]

try:  # Telethon is installed in production, but keep imports graceful.
    from telethon import TelegramClient, events
except ImportError:  # pragma: no cover - exercised only in minimal installs
    TelegramClient = None  # type: ignore[assignment,misc]
    events = None  # type: ignore[assignment,misc]


bot: Any | None = None
dp: Any | None = None
_polling_task: asyncio.Task | None = None

mtproto_client: Any | None = None
_mtproto_task: asyncio.Task | None = None
_mtproto_authorized = False
_mtproto_error: str | None = None
_mtproto_me_id: int | None = None


def _chat_title(chat: Any) -> str:
    first = getattr(chat, "first_name", None)
    last = getattr(chat, "last_name", None)
    title = " ".join(part for part in (first, last) if part).strip()
    return title or getattr(chat, "title", None) or str(getattr(chat, "id", "Telegram chat"))


def _message_body(message: Any) -> str:
    body = getattr(message, "text", None) or getattr(message, "caption", None)
    if body:
        return str(body)
    if getattr(message, "photo", None):
        return "[Фото]"
    if _message_document(message) is not None:
        return "[Файл]"
    content_type = getattr(message, "content_type", None) or "message"
    return f"[{content_type}]"


def _message_document(message: Any) -> Any | None:
    """Photos sent as files remain downloadable documents, not previews."""

    if getattr(message, "photo", None):
        return None
    return getattr(message, "document", None)


def _document_metadata(document: Any) -> tuple[str, str | None, str | None]:
    if document is None:
        return "", None, None
    file_id = getattr(document, "file_id", None)
    filename = getattr(document, "file_name", None)
    mime_type = getattr(document, "mime_type", None)
    if not filename:
        for attribute in getattr(document, "attributes", ()) or ():
            filename = getattr(attribute, "file_name", None)
            if filename:
                break
    return str(file_id) if file_id else "", str(filename)[:255] if filename else None, str(mime_type)[:255] if mime_type else None


def _reaction_summary(reactions: Any) -> list[dict[str, int | str]]:
    """Extract visible counts from MTProto/Bot API reaction objects."""

    if reactions is None:
        return []
    results = getattr(reactions, "results", None)
    if results is None:
        results = reactions
    if not isinstance(results, (list, tuple)):
        return []
    counts: dict[str, int] = {}
    for item in results:
        reaction = getattr(item, "reaction", item)
        emoji = getattr(reaction, "emoticon", None) or getattr(reaction, "emoji", None)
        if emoji is None and getattr(reaction, "document_id", None) is not None:
            emoji = "✨"
        if emoji is None and type(reaction).__name__ == "ReactionPaid":
            emoji = "⭐"
        count = int(getattr(item, "count", 1) or 0)
        if emoji and count > 0:
            counts[str(emoji)] = counts.get(str(emoji), 0) + count
    return [{"emoji": emoji, "count": count} for emoji, count in counts.items()]


def _store_reactions(telegram_chat_id: int, telegram_message_id: int, reactions: Any) -> None:
    summary = _reaction_summary(reactions)
    with SessionLocal() as db:
        chat_id = db.scalar(select(TelegramChat.id).where(TelegramChat.telegram_chat_id == telegram_chat_id))
        if chat_id is None:
            return
        db.execute(
            update(TelegramMessage)
            .where(TelegramMessage.chat_id == chat_id, TelegramMessage.telegram_message_id == telegram_message_id)
            .values(reactions_json=json.dumps(summary, ensure_ascii=False))
        )
        db.commit()


def _normalise_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalise_chat_type(value: Any) -> str:
    return str(getattr(value, "value", value) or "private").lower()


def _persist_message(
    *,
    telegram_chat_id: int,
    title: str,
    username: str | None,
    chat_type: str,
    business_connection_id: str | None,
    telegram_message_id: int,
    sender_id: int | None,
    sender_name: str,
    sender_username: str | None,
    body: str,
    has_photo: bool,
    photo_file_id: str | None,
    has_document: bool = False,
    document_file_id: str | None = None,
    document_name: str | None = None,
    document_mime_type: str | None = None,
    reactions: Any = None,
    direction: str,
    telegram_date: datetime | None,
    _retry_on_conflict: bool = True,
) -> None:
    """Persist one message, shared by Bot API and MTProto handlers."""

    with SessionLocal() as db:
        chat_type = _normalise_chat_type(chat_type)
        # For private chats the peer id is the chat id.  Bot API business
        # updates may report messages sent by the connected account through
        # the same handler as incoming messages.  The sender mismatch is an
        # unambiguous outbound signal and must win over the handler hint.
        effective_direction = direction
        if chat_type == "private" and sender_id is not None:
            effective_direction = "inbound" if sender_id == telegram_chat_id else "outbound"
        # A deleted student/peer is intentionally kept out of the local
        # platform forever.  Check this before creating the automatic student
        # account, otherwise the next Telegram update would resurrect it.
        ignored = db.scalar(
            select(TelegramIgnoredChat.id).where(
                TelegramIgnoredChat.telegram_chat_id == telegram_chat_id,
            )
        )
        if ignored is not None:
            return
        if (
            effective_direction == "inbound"
            and chat_type == "private"
            and telegram_chat_id > 0
            and telegram_chat_id != (_mtproto_me_id or 0)
        ):
            student = db.scalar(select(User).where(User.telegram_user_id == telegram_chat_id))
            student_name = title if title and not title.isdigit() else sender_name
            if student is None:
                student = User(
                    email=f"telegram-{telegram_chat_id}@students-idioma.com",
                    full_name=student_name,
                    role="student",
                    password_hash=hash_password(secrets.token_urlsafe(32)),
                    telegram_user_id=telegram_chat_id,
                    telegram_username=username or sender_username,
                )
                db.add(student)
            elif student.role == "student" and chat_type == "private" and student_name:
                # Keep auto-created student metadata aligned with the actual
                # Telegram peer, not the connected account that sent a copy.
                student.full_name = student_name
                peer_username = username or sender_username
                if peer_username and student.telegram_username != peer_username:
                    student.telegram_username = peer_username

        chat = db.scalar(select(TelegramChat).where(TelegramChat.telegram_chat_id == telegram_chat_id))
        if chat is None:
            chat = TelegramChat(
                telegram_chat_id=telegram_chat_id,
                title=title,
                username=username,
                chat_type=chat_type,
                business_connection_id=business_connection_id,
            )
            db.add(chat)
            db.flush()
        else:
            chat.title = title or chat.title
            chat.username = username
            chat.chat_type = chat_type or chat.chat_type
            if business_connection_id:
                chat.business_connection_id = business_connection_id

        deleted_locally = db.scalar(
            select(TelegramDeletedMessage.id).where(
                TelegramDeletedMessage.chat_id == chat.id,
                TelegramDeletedMessage.telegram_message_id == telegram_message_id,
            )
        )
        if deleted_locally is not None:
            db.commit()
            return

        stored = db.scalar(
            select(TelegramMessage).where(
                TelegramMessage.chat_id == chat.id,
                TelegramMessage.telegram_message_id == telegram_message_id,
            )
        )
        if stored is None and telegram_message_id > 0:
            if effective_direction == "inbound":
                previous_message_id = db.scalar(
                    select(TelegramMessage.id)
                    .where(TelegramMessage.chat_id == chat.id)
                    .order_by(TelegramMessage.id.desc())
                    .limit(1)
                )
                reader_ids = db.scalars(select(User.id).where(User.role.in_(("admin", "teacher")))).all()
                existing_reader_ids = set(
                    db.scalars(
                        select(TelegramChatReadState.user_id).where(
                            TelegramChatReadState.chat_id == chat.id,
                            TelegramChatReadState.user_id.in_(reader_ids),
                        )
                    ).all()
                )
                db.add_all(
                    TelegramChatReadState(
                        chat_id=chat.id,
                        user_id=reader_id,
                        last_read_message_id=previous_message_id,
                    )
                    for reader_id in reader_ids
                    if reader_id not in existing_reader_ids
                )
            db.add(
                TelegramMessage(
                    chat_id=chat.id,
                    telegram_message_id=telegram_message_id,
                    sender_telegram_id=sender_id,
                    sender_name=sender_name,
                    sender_username=sender_username,
                    body=body,
                    has_photo=has_photo,
                    photo_file_id=photo_file_id,
                    has_document=has_document,
                    document_file_id=document_file_id,
                    document_name=document_name,
                    document_mime_type=document_mime_type,
                    reactions_json=json.dumps(_reaction_summary(reactions), ensure_ascii=False) if reactions is not None else None,
                    direction=effective_direction,
                    telegram_date=telegram_date,
                )
            )
        elif stored is not None:
            stored.body = body
            stored.direction = effective_direction
            # A second Telegram transport can supply less metadata than the
            # first. Never erase a known photo when that duplicate arrives.
            stored.has_photo = bool(stored.has_photo) or has_photo
            if photo_file_id:
                stored.photo_file_id = photo_file_id
            stored.has_document = bool(stored.has_document) or has_document
            if document_file_id:
                stored.document_file_id = document_file_id
            if document_name:
                stored.document_name = document_name
            if document_mime_type:
                stored.document_mime_type = document_mime_type
            if reactions is not None:
                stored.reactions_json = json.dumps(_reaction_summary(reactions), ensure_ascii=False)
        chat.updated_at = telegram_date or datetime.now(timezone.utc)
        try:
            db.commit()
        except IntegrityError:
            # Bot API and MTProto can receive the same inbound update at
            # nearly the same time. One transaction wins; retry once after
            # rolling back so the second one sees the saved student/message.
            db.rollback()
            if not _retry_on_conflict:
                raise
            _persist_message(
                telegram_chat_id=telegram_chat_id,
                title=title,
                username=username,
                chat_type=chat_type,
                business_connection_id=business_connection_id,
                telegram_message_id=telegram_message_id,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_username=sender_username,
                body=body,
                has_photo=has_photo,
                photo_file_id=photo_file_id,
                has_document=has_document,
                document_file_id=document_file_id,
                document_name=document_name,
                document_mime_type=document_mime_type,
                reactions=reactions,
                direction=direction,
                telegram_date=telegram_date,
                _retry_on_conflict=False,
            )


def persist_telegram_message(message: Any, direction: str = "inbound") -> None:
    """Upsert an aiogram message and its chat in PostgreSQL."""

    telegram_chat = message.chat
    sender = getattr(message, "from_user", None)
    sender_id = int(sender.id) if sender and getattr(sender, "id", None) is not None else None
    sender_name = (
        " ".join(
            part
            for part in (getattr(sender, "first_name", None), getattr(sender, "last_name", None))
            if part
        ).strip()
        if sender
        else "idioma"
    )
    sender_name = sender_name or getattr(sender, "username", None) or "Telegram user"
    photos = getattr(message, "photo", None) or []
    document = _message_document(message)
    document_file_id, document_name, document_mime_type = _document_metadata(document)
    _persist_message(
        telegram_chat_id=int(telegram_chat.id),
        title=_chat_title(telegram_chat),
        username=getattr(telegram_chat, "username", None),
        chat_type=getattr(telegram_chat, "type", "private"),
        business_connection_id=getattr(message, "business_connection_id", None),
        telegram_message_id=int(message.message_id),
        sender_id=sender_id,
        sender_name=sender_name,
        sender_username=getattr(sender, "username", None),
        body=_message_body(message),
        has_photo=bool(photos),
        photo_file_id=str(photos[-1].file_id) if photos else None,
        has_document=document is not None,
        document_file_id=document_file_id,
        document_name=document_name,
        document_mime_type=document_mime_type,
        reactions=getattr(message, "reactions", None),
        direction=direction,
        telegram_date=_normalise_date(getattr(message, "date", None)),
    )


def _mtproto_entity_title(entity: Any) -> str:
    first = getattr(entity, "first_name", None)
    last = getattr(entity, "last_name", None)
    title = " ".join(part for part in (first, last) if part).strip()
    return title or getattr(entity, "title", None) or getattr(entity, "username", None) or str(entity.id)


def _mtproto_chat_type(entity: Any) -> str:
    name = entity.__class__.__name__.lower()
    if "channel" in name:
        return "channel"
    if "chat" in name:
        return "group"
    return "private"


def _sync_private_dialog_student(db: Any, entity: Any, telegram_chat_id: int, title: str) -> None:
    """Ensure every real private user dialog is available for assignment."""

    if (
        telegram_chat_id <= 0
        or telegram_chat_id == (_mtproto_me_id or 0)
        or _mtproto_chat_type(entity) != "private"
        or bool(getattr(entity, "bot", False))
    ):
        return
    username = getattr(entity, "username", None)
    student = db.scalar(
        select(User).where(
            User.role == "student",
            User.telegram_user_id == telegram_chat_id,
        )
    )
    if student is None:
        db.add(
            User(
                email=f"telegram-{telegram_chat_id}@students-idioma.com",
                full_name=title,
                role="student",
                password_hash=hash_password(secrets.token_urlsafe(32)),
                telegram_user_id=telegram_chat_id,
                telegram_username=username,
            )
        )
    else:
        student.full_name = title
        student.telegram_username = username


def _repair_outbound_directions(own_telegram_id: int) -> None:
    """Repair records previously misclassified by Bot API business updates."""

    with SessionLocal() as db:
        db.execute(
            update(TelegramMessage)
            .where(
                TelegramMessage.sender_telegram_id == own_telegram_id,
                TelegramMessage.direction != "outbound",
            )
            .values(direction="outbound")
        )
        # Older builds could create the connected MTProto account as a student
        # and assign its id to a teacher.  Deactivate that stale assignment;
        # the account itself remains available for administrator cleanup.
        own_students = db.scalars(
            select(User).where(
                User.role == "student",
                User.telegram_user_id == own_telegram_id,
            )
        ).all()
        for student in own_students:
            db.execute(
                update(TeacherStudentAssignment)
                .where(TeacherStudentAssignment.student_id == student.id)
                .values(status="inactive")
            )
        db.commit()


async def persist_mtproto_message(message: Any, entity: Any | None = None, direction: str | None = None) -> None:
    """Persist a Telethon message; ``direction`` defaults to ``message.out``."""

    chat_id = getattr(message, "chat_id", None)
    if chat_id is None and entity is not None:
        chat_id = getattr(entity, "id", None)
    if chat_id is None:
        return
    chat_id = int(chat_id)
    # Always resolve the peer from the message chat id first.  In particular,
    # ``message.sender`` is the connected account for outgoing messages and is
    # not the conversation title.
    resolved_entity = None
    if mtproto_client is not None:
        try:
            resolved_entity = await mtproto_client.get_entity(chat_id)
        except Exception:
            resolved_entity = None
    if resolved_entity is None:
        try:
            resolved_entity = await message.get_chat()
        except Exception:
            resolved_entity = None
    entity = resolved_entity or entity
    sender = getattr(message, "sender", None)
    if sender is None:
        try:
            sender = await message.get_sender()
        except Exception:
            sender = None
    sender_id = int(getattr(sender, "id", 0)) if sender is not None and getattr(sender, "id", None) is not None else None
    sender_name = _mtproto_entity_title(sender) if sender is not None else "idioma"
    sender_username = getattr(sender, "username", None) if sender is not None else None
    title = _mtproto_entity_title(entity) if entity is not None else str(chat_id)
    username = getattr(entity, "username", None) if entity is not None else None
    chat_type = _mtproto_chat_type(entity) if entity is not None else "private"
    document = _message_document(message)
    document_file_id, document_name, document_mime_type = _document_metadata(document)
    await asyncio.to_thread(
        _persist_message,
        telegram_chat_id=chat_id,
        title=title,
        username=username,
        chat_type=chat_type,
        business_connection_id=None,
        telegram_message_id=int(getattr(message, "id", 0) or 0),
        sender_id=sender_id,
        sender_name=sender_name,
        sender_username=sender_username,
        body=_message_body(message),
        has_photo=bool(getattr(message, "photo", None)),
        photo_file_id=None,
        has_document=document is not None,
        document_file_id=document_file_id,
        document_name=document_name,
        document_mime_type=document_mime_type,
        reactions=getattr(message, "reactions", None),
        direction=direction or ("outbound" if getattr(message, "out", False) else "inbound"),
        telegram_date=_normalise_date(getattr(message, "date", None)),
    )


async def _sync_mtproto_dialogs() -> None:
    if mtproto_client is None or not settings.telegram_sync_dialogs:
        return
    limit = settings.telegram_history_limit or None
    try:
        # Load the dialog list first. Importing the entire history of a large
        # chat can take a while; a teacher must still see every available chat
        # in the inbox immediately instead of waiting for older histories.
        dialogs = [dialog async for dialog in mtproto_client.iter_dialogs()]
        print(f"Telegram MTProto discovered {len(dialogs)} dialogs")

        for dialog in dialogs:
            entity = dialog.entity
            if await asyncio.to_thread(_is_ignored_chat_id, int(dialog.id)):
                continue
            # Ensure dialogs with no messages still appear in the chat list.
            with SessionLocal() as db:
                title = _mtproto_entity_title(entity)
                chat = db.scalar(select(TelegramChat).where(TelegramChat.telegram_chat_id == int(dialog.id)))
                if chat is None:
                    db.add(
                        TelegramChat(
                            telegram_chat_id=int(dialog.id),
                            title=title,
                            username=getattr(entity, "username", None),
                            chat_type=_mtproto_chat_type(entity),
                        )
                    )
                else:
                    chat.title = title
                    chat.username = getattr(entity, "username", None)
                    chat.chat_type = _mtproto_chat_type(entity)
                _sync_private_dialog_student(db, entity, int(dialog.id), title)
                db.commit()

        # Histories are intentionally a second pass so the chat list is usable
        # even while Telegram is still serving a long-running import.
        for dialog in dialogs:
            entity = dialog.entity
            if await asyncio.to_thread(_is_ignored_chat_id, int(dialog.id)):
                continue
            latest_stored_message_id = await asyncio.to_thread(
                _latest_stored_message_id,
                int(dialog.id),
            )
            history_kwargs: dict[str, Any] = {"limit": limit, "reverse": True}
            if latest_stored_message_id is not None:
                # A restart should load only new messages. Re-importing every
                # history on a small VPS caused enough database work to make
                # the server unresponsive.
                history_kwargs["min_id"] = latest_stored_message_id
            async for message in mtproto_client.iter_messages(entity, **history_kwargs):
                await persist_mtproto_message(message, entity=entity)
        print("Telegram MTProto history sync complete")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # A single inaccessible/deleted dialog should not stop real-time sync.
        print(f"Telegram MTProto history sync partially failed: {exc}")


def _latest_stored_message_id(telegram_chat_id: int) -> int | None:
    """Return the last stored or locally deleted Telegram message ID."""

    with SessionLocal() as db:
        latest_message_id = db.scalar(
            select(func.max(TelegramMessage.telegram_message_id))
            .join(TelegramChat, TelegramMessage.chat_id == TelegramChat.id)
            .where(TelegramChat.telegram_chat_id == telegram_chat_id)
        )
        latest_deleted_id = db.scalar(
            select(func.max(TelegramDeletedMessage.telegram_message_id))
            .join(TelegramChat, TelegramDeletedMessage.chat_id == TelegramChat.id)
            .where(TelegramChat.telegram_chat_id == telegram_chat_id)
        )
        candidates = [value for value in (latest_message_id, latest_deleted_id) if value is not None]
        return max(candidates) if candidates else None


def _is_ignored_chat_id(telegram_chat_id: int) -> bool:
    with SessionLocal() as db:
        return db.scalar(
            select(TelegramIgnoredChat.id).where(
                TelegramIgnoredChat.telegram_chat_id == telegram_chat_id,
            )
        ) is not None


async def _mtproto_runner() -> None:
    try:
        await _sync_mtproto_dialogs()
        await mtproto_client.run_until_disconnected()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        global _mtproto_error
        _mtproto_error = str(exc)
        print(f"Telegram MTProto stopped: {exc}")


async def _start_mtproto() -> None:
    global mtproto_client, _mtproto_task, _mtproto_authorized, _mtproto_error, _mtproto_me_id
    _mtproto_authorized = False
    _mtproto_error = None
    if not settings.telegram_mtproto_enabled:
        return
    if TelegramClient is None:
        _mtproto_error = "Telethon is not installed"
        print("Telegram MTProto disabled: install Telethon to enable it")
        return
    if not settings.telegram_api_id or not (settings.telegram_api_hash or "").strip():
        _mtproto_error = "TELEGRAM_API_ID and TELEGRAM_API_HASH are required"
        print("Telegram MTProto disabled: API credentials are not configured")
        return
    session_path = Path(settings.telegram_session_path).expanduser()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mtproto_client = TelegramClient(str(session_path), settings.telegram_api_id, settings.telegram_api_hash)
        await mtproto_client.connect()
        if not await mtproto_client.is_user_authorized():
            _mtproto_error = "session is not authorized; run scripts/telegram-login.cmd"
            await mtproto_client.disconnect()
            mtproto_client = None
            print("Telegram MTProto is not authorized; run scripts/telegram-login.cmd")
            return
        me = await mtproto_client.get_me()
        _mtproto_me_id = int(me.id) if me and getattr(me, "id", None) is not None else None
        if _mtproto_me_id is not None:
            await asyncio.to_thread(_repair_outbound_directions, _mtproto_me_id)

        @mtproto_client.on(events.NewMessage)
        async def on_mtproto_message(event: Any) -> None:
            await persist_mtproto_message(event.message)

        @mtproto_client.on(events.MessageEdited)
        async def on_mtproto_edited(event: Any) -> None:
            await persist_mtproto_message(event.message)

        @mtproto_client.on(events.Raw)
        async def on_mtproto_reactions(update: Any) -> None:
            if update.__class__.__name__ != "UpdateMessageReactions":
                return
            try:
                from telethon import utils

                peer_id = int(utils.get_peer_id(update.peer))
                await asyncio.to_thread(_store_reactions, peer_id, int(update.msg_id), update.reactions)
            except Exception:
                # The next conversation refresh also checks Telegram's latest
                # reaction state; a malformed/unknown peer must not stop sync.
                pass

        _mtproto_authorized = True
        if _mtproto_task is None or _mtproto_task.done():
            _mtproto_task = asyncio.create_task(_mtproto_runner(), name="telegram-mtproto")
        print(f"Telegram MTProto started for account {_mtproto_me_id or 'unknown'}")
    except Exception as exc:
        _mtproto_error = str(exc)
        print(f"Telegram MTProto disabled: {exc}")
        if mtproto_client is not None:
            try:
                await mtproto_client.disconnect()
            except Exception:
                pass
        mtproto_client = None


async def send_telegram_text(chat: TelegramChat, body: str) -> None:
    # Prefer the user account whenever it is authorized. This avoids the Bot
    # API Business restriction for contacts that have not written recently.
    if settings.telegram_mtproto_enabled:
        if mtproto_client is None or not _mtproto_authorized or not mtproto_client.is_connected():
            raise RuntimeError("Telegram MTProto не авторизован. Запустите scripts/telegram-login.cmd")
        try:
            entity = await mtproto_client.get_input_entity(int(chat.telegram_chat_id))
            sent = await mtproto_client.send_message(entity, body)
            await persist_mtproto_message(sent, direction="outbound")
            return
        except Exception as exc:
            raise RuntimeError(f"Не удалось отправить сообщение через Telegram MTProto: {exc}") from exc

    if bot is None:
        raise RuntimeError("Telegram не настроен: укажите TELEGRAM_BOT_TOKEN или включите MTProto")
    try:
        send_kwargs = {"chat_id": chat.telegram_chat_id, "text": body}
        if chat.business_connection_id:
            send_kwargs["business_connection_id"] = chat.business_connection_id
        sent = await bot.send_message(**send_kwargs)
    except Exception as exc:
        raise RuntimeError(f"Не удалось отправить сообщение в Telegram: {exc}") from exc
    persist_telegram_message(sent, direction="outbound")


async def send_telegram_photo(chat: TelegramChat, data: bytes, caption: str, filename: str) -> None:
    """Send a photo as the connected account, then store its Telegram message."""

    if settings.telegram_mtproto_enabled:
        if mtproto_client is None or not _mtproto_authorized or not mtproto_client.is_connected():
            raise RuntimeError("Telegram MTProto не подключён")
        try:
            entity = await mtproto_client.get_input_entity(int(chat.telegram_chat_id))
            stream = io.BytesIO(data)
            stream.name = filename
            sent = await mtproto_client.send_file(entity, stream, caption=caption, force_document=False)
            await persist_mtproto_message(sent, direction="outbound")
            return
        except Exception as exc:
            raise RuntimeError(f"Не удалось отправить фото через Telegram: {exc}") from exc

    if bot is None:
        raise RuntimeError("Telegram не подключён")
    try:
        from aiogram.types import BufferedInputFile

        send_kwargs = {
            "chat_id": chat.telegram_chat_id,
            "photo": BufferedInputFile(data, filename=filename),
            "caption": caption or None,
        }
        if chat.business_connection_id:
            send_kwargs["business_connection_id"] = chat.business_connection_id
        sent = await bot.send_photo(**send_kwargs)
        persist_telegram_message(sent, direction="outbound")
    except Exception as exc:
        raise RuntimeError(f"Не удалось отправить фото через Telegram: {exc}") from exc


async def send_telegram_document(chat: TelegramChat, data: bytes, caption: str, filename: str) -> None:
    """Send any non-photo attachment as a downloadable Telegram document."""

    if settings.telegram_mtproto_enabled:
        if mtproto_client is None or not _mtproto_authorized or not mtproto_client.is_connected():
            raise RuntimeError("Telegram MTProto не подключён")
        try:
            entity = await mtproto_client.get_input_entity(int(chat.telegram_chat_id))
            stream = io.BytesIO(data)
            stream.name = filename
            sent = await mtproto_client.send_file(entity, stream, caption=caption, force_document=True)
            await persist_mtproto_message(sent, direction="outbound")
            return
        except Exception as exc:
            raise RuntimeError(f"Не удалось отправить файл через Telegram: {exc}") from exc

    if bot is None:
        raise RuntimeError("Telegram не подключён")
    try:
        from aiogram.types import BufferedInputFile

        send_kwargs = {
            "chat_id": chat.telegram_chat_id,
            "document": BufferedInputFile(data, filename=filename),
            "caption": caption or None,
        }
        if chat.business_connection_id:
            send_kwargs["business_connection_id"] = chat.business_connection_id
        sent = await bot.send_document(**send_kwargs)
        persist_telegram_message(sent, direction="outbound")
    except Exception as exc:
        raise RuntimeError(f"Не удалось отправить файл через Telegram: {exc}") from exc


async def telegram_media_metadata(telegram_chat_id: int, message_ids: list[int]) -> dict[int, dict]:
    """Discover old photos and documents without downloading their contents."""

    if not message_ids or mtproto_client is None or not _mtproto_authorized or not mtproto_client.is_connected():
        return {}
    entity = await mtproto_client.get_input_entity(telegram_chat_id)
    messages = await mtproto_client.get_messages(entity, ids=message_ids)
    metadata = {}
    for message in messages:
        if message is None:
            continue
        document = _message_document(message)
        file_id, filename, mime_type = _document_metadata(document)
        metadata[int(message.id)] = {
            "has_photo": bool(getattr(message, "photo", None)),
            "has_document": document is not None,
            "document_file_id": file_id or None,
            "document_name": filename,
            "document_mime_type": mime_type,
        }
    return metadata


async def telegram_photo_flags(telegram_chat_id: int, message_ids: list[int]) -> dict[int, bool]:
    """Check old imported messages in one MTProto request."""

    if not message_ids or mtproto_client is None or not _mtproto_authorized or not mtproto_client.is_connected():
        return {}
    entity = await mtproto_client.get_input_entity(telegram_chat_id)
    messages = await mtproto_client.get_messages(entity, ids=message_ids)
    return {int(message.id): bool(getattr(message, "photo", None)) for message in messages if message is not None}


async def download_telegram_photo(
    telegram_chat_id: int, telegram_message_id: int, photo_file_id: str | None
) -> bytes:
    """Download only the requested photo; callers enforce chat access."""

    if mtproto_client is not None and _mtproto_authorized and mtproto_client.is_connected():
        entity = await mtproto_client.get_input_entity(telegram_chat_id)
        message = await mtproto_client.get_messages(entity, ids=telegram_message_id)
        if message is None or not getattr(message, "photo", None):
            raise FileNotFoundError("Фото больше не доступно в Telegram")
        data = await mtproto_client.download_media(message, file=bytes)
        if isinstance(data, bytes):
            return data
    if bot is not None and photo_file_id:
        file_info = await bot.get_file(photo_file_id)
        stream = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=stream)
        return stream.getvalue()
    raise FileNotFoundError("Фото недоступно в Telegram")


async def download_telegram_document(
    telegram_chat_id: int, telegram_message_id: int, document_file_id: str | None
) -> bytes:
    """Download a document only after platform chat authorization."""

    if mtproto_client is not None and _mtproto_authorized and mtproto_client.is_connected():
        entity = await mtproto_client.get_input_entity(telegram_chat_id)
        message = await mtproto_client.get_messages(entity, ids=telegram_message_id)
        if message is not None and _message_document(message) is not None:
            data = await mtproto_client.download_media(message, file=bytes)
            if isinstance(data, bytes):
                return data
    if bot is not None and document_file_id:
        file_info = await bot.get_file(document_file_id)
        stream = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=stream)
        return stream.getvalue()
    raise FileNotFoundError("Файл недоступен в Telegram")


async def _polling_runner() -> None:
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # do not bring down the web API on Telegram errors
        print(f"Telegram polling stopped: {exc}")


async def _start_bot_api() -> None:
    global bot, dp, _polling_task
    token = (settings.telegram_bot_token or "").strip().strip('"').strip("'")
    if not token:
        print("Telegram Bot API disabled: TELEGRAM_BOT_TOKEN is not configured")
        return
    if Bot is None or Dispatcher is None:
        print("Telegram Bot API disabled: install aiogram to enable it")
        return
    if bot is None:
        try:
            bot = Bot(token)
        except Exception as exc:
            print(f"Telegram Bot API disabled: invalid TELEGRAM_BOT_TOKEN ({exc})")
            bot = None
            dp = None
            return
    if not settings.telegram_polling_enabled:
        print("Telegram polling disabled: TELEGRAM_POLLING_ENABLED=false")
        return
    if _polling_task and not _polling_task.done():
        return

    dp = Dispatcher()

    @dp.business_connection()
    async def on_business_connection(connection: BusinessConnection) -> None:
        print(f"Telegram business connection {connection.id}: enabled={connection.is_enabled}")

    @dp.business_message()
    async def on_business_message(message: Message) -> None:
        persist_telegram_message(message, direction="inbound")

    @dp.message()
    async def on_regular_message(message: Message) -> None:
        persist_telegram_message(message, direction="inbound")

    @dp.edited_business_message()
    async def on_edited_business_message(message: Message) -> None:
        persist_telegram_message(message, direction="inbound")

    @dp.edited_message()
    async def on_edited_message(message: Message) -> None:
        persist_telegram_message(message, direction="inbound")

    print("Telegram Bot API polling started")
    _polling_task = asyncio.create_task(_polling_runner(), name="telegram-polling")


async def start_telegram_polling() -> None:
    # Start both integrations independently: one may be disabled while the
    # other is active (for example, MTProto-only deployments).
    await _start_bot_api()
    await _start_mtproto()


async def stop_telegram_polling() -> None:
    global bot, dp, _polling_task, mtproto_client, _mtproto_task, _mtproto_authorized, _mtproto_me_id
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    _polling_task = None
    if bot is not None:
        await bot.session.close()
    bot = None
    dp = None

    if _mtproto_task and not _mtproto_task.done():
        _mtproto_task.cancel()
        try:
            await _mtproto_task
        except asyncio.CancelledError:
            pass
    _mtproto_task = None
    if mtproto_client is not None:
        try:
            await mtproto_client.disconnect()
        except Exception:
            pass
    mtproto_client = None
    _mtproto_authorized = False
    _mtproto_me_id = None


if __name__ == "__main__":
    async def main() -> None:
        await start_telegram_polling()
        tasks = [task for task in (_polling_task, _mtproto_task) if task]
        if tasks:
            await asyncio.gather(*tasks)

    asyncio.run(main())
