import asyncio
import io
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.api.routes import get_chat_document, get_chat_photo, post_chat_document, post_chat_photo
from app.models import telegram as _telegram_models  # noqa: F401
from app.models.telegram import TelegramChat, TelegramDocument, TelegramMessage, TelegramPhoto
from app.models.user import User
from app.services.telegram import get_telegram_document, get_telegram_photo, image_mime_type
from app.tg import download_telegram_photo, send_telegram_document, send_telegram_photo, telegram_media_metadata, telegram_photo_flags


JPEG = b"\xff\xd8\xff\xe0" + b"test-photo"


class TelegramPhotoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = User(email="admin@local.test", full_name="Admin", role="admin", password_hash="unused")
        self.teacher = User(email="teacher@local.test", full_name="Teacher", role="teacher", password_hash="unused")
        self.chat = TelegramChat(telegram_chat_id=12345, title="Student", chat_type="private")
        self.message = TelegramMessage(
            chat=self.chat,
            telegram_message_id=42,
            sender_name="Student",
            body="[Фото]",
            direction="inbound",
            has_photo=True,
        )
        self.db.add_all([self.admin, self.teacher, self.message])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_photo_access_is_scoped_to_chat(self):
        with patch("app.tg.download_telegram_photo", new_callable=AsyncMock, return_value=JPEG) as downloader:
            data, mime = asyncio.run(get_telegram_photo(self.db, self.admin, self.chat.id, self.message.id))
            self.assertEqual((data, mime), (JPEG, "image/jpeg"))
            self.assertEqual(downloader.await_count, 1)
            self.assertEqual(self.db.query(TelegramPhoto).count(), 1)
            # The second read is served from the retained local history.
            asyncio.run(get_telegram_photo(self.db, self.admin, self.chat.id, self.message.id))
            self.assertEqual(downloader.await_count, 1)

        with self.assertRaises(HTTPException) as denied:
            asyncio.run(get_telegram_photo(self.db, self.teacher, self.chat.id, self.message.id))
        self.assertEqual(denied.exception.status_code, 403)

        other_chat = TelegramChat(telegram_chat_id=999, title="Other")
        self.db.add(other_chat)
        self.db.commit()
        with self.assertRaises(HTTPException) as missing:
            asyncio.run(get_telegram_photo(self.db, self.admin, other_chat.id, self.message.id))
        self.assertEqual(missing.exception.status_code, 404)

    def test_mtproto_send_and_old_history_detection(self):
        sent_message = SimpleNamespace(id=99, photo=object())
        fake_client = SimpleNamespace(
            is_connected=lambda: True,
            get_input_entity=AsyncMock(return_value="peer"),
            send_file=AsyncMock(return_value=sent_message),
            get_messages=AsyncMock(return_value=[SimpleNamespace(id=42, photo=object())]),
            download_media=AsyncMock(return_value=JPEG),
        )
        with (
            patch("app.tg.settings.telegram_mtproto_enabled", True),
            patch("app.tg.mtproto_client", fake_client),
            patch("app.tg._mtproto_authorized", True),
            patch("app.tg.persist_mtproto_message", new_callable=AsyncMock) as persist,
        ):
            asyncio.run(send_telegram_photo(self.chat, JPEG, "caption", "lesson.jpg"))
            sent_stream = fake_client.send_file.await_args.args[1]
            self.assertIsInstance(sent_stream, io.BytesIO)
            self.assertEqual(sent_stream.getvalue(), JPEG)
            self.assertEqual(fake_client.send_file.await_args.kwargs["caption"], "caption")
            persist.assert_awaited_once_with(sent_message, direction="outbound")
            self.assertEqual(asyncio.run(telegram_photo_flags(12345, [42])), {42: True})
            fake_client.get_messages.return_value = SimpleNamespace(id=42, photo=object())
            self.assertEqual(asyncio.run(download_telegram_photo(12345, 42, None)), JPEG)

    def test_rejects_non_image_payload(self):
        self.assertIsNone(image_mime_type(b"not an image"))

    def test_photo_route_validates_payload_and_protects_read(self):
        upload = SimpleNamespace(content_type="image/jpeg", filename="lesson.jpg", read=AsyncMock(return_value=JPEG))
        with patch("app.api.routes.send_telegram_photo_message", new_callable=AsyncMock, return_value={"sent": True}) as sender:
            self.assertEqual(
                asyncio.run(post_chat_photo(self.chat.id, upload, "lesson", self.admin, self.db)),
                {"sent": True},
            )
            sender.assert_awaited_once_with(self.db, self.admin, self.chat.id, JPEG, "lesson.jpg", "lesson")

        bad_upload = SimpleNamespace(content_type="image/jpeg", filename="fake.jpg", read=AsyncMock(return_value=b"fake"))
        with self.assertRaises(HTTPException) as invalid:
            asyncio.run(post_chat_photo(self.chat.id, bad_upload, "", self.admin, self.db))
        self.assertEqual(invalid.exception.status_code, 415)

        with self.assertRaises(HTTPException) as denied:
            asyncio.run(get_chat_photo(self.chat.id, self.message.id, self.teacher, self.db))
        self.assertEqual(denied.exception.status_code, 403)

    def test_document_send_download_and_access(self):
        data = b"course materials"
        self.message.has_photo = False
        self.message.has_document = True
        self.message.document_name = "lesson.pdf"
        self.message.document_mime_type = "application/pdf"
        self.db.commit()
        with patch("app.tg.download_telegram_document", new_callable=AsyncMock, return_value=data) as downloader:
            self.assertEqual(
                asyncio.run(get_telegram_document(self.db, self.admin, self.chat.id, self.message.id)),
                (data, "application/pdf", "lesson.pdf"),
            )
            self.assertEqual(self.db.query(TelegramDocument).count(), 1)
            asyncio.run(get_telegram_document(self.db, self.admin, self.chat.id, self.message.id))
            self.assertEqual(downloader.await_count, 1)
        with self.assertRaises(HTTPException) as denied:
            asyncio.run(get_chat_document(self.chat.id, self.message.id, self.teacher, self.db))
        self.assertEqual(denied.exception.status_code, 403)

        fake_client = SimpleNamespace(
            is_connected=lambda: True,
            get_input_entity=AsyncMock(return_value="peer"),
            send_file=AsyncMock(return_value=SimpleNamespace(id=50, document=object())),
            get_messages=AsyncMock(return_value=[SimpleNamespace(id=42, photo=None, document=SimpleNamespace(mime_type="application/pdf", attributes=[SimpleNamespace(file_name="lesson.pdf")]))]),
        )
        with (
            patch("app.tg.settings.telegram_mtproto_enabled", True),
            patch("app.tg.mtproto_client", fake_client),
            patch("app.tg._mtproto_authorized", True),
            patch("app.tg.persist_mtproto_message", new_callable=AsyncMock) as persist,
        ):
            asyncio.run(send_telegram_document(self.chat, data, "caption", "lesson.pdf"))
            self.assertTrue(fake_client.send_file.await_args.kwargs["force_document"])
            persist.assert_awaited_once()
            self.assertEqual(asyncio.run(telegram_media_metadata(12345, [42]))[42]["document_name"], "lesson.pdf")

    def test_document_route_accepts_generic_file(self):
        upload = SimpleNamespace(filename="notes.txt", read=AsyncMock(return_value=b"notes"))
        with patch("app.api.routes.send_telegram_document_message", new_callable=AsyncMock, return_value={"sent": True}) as sender:
            self.assertEqual(
                asyncio.run(post_chat_document(self.chat.id, upload, "", self.admin, self.db)),
                {"sent": True},
            )
            sender.assert_awaited_once_with(self.db, self.admin, self.chat.id, b"notes", "notes.txt", "")


if __name__ == "__main__":
    unittest.main()
