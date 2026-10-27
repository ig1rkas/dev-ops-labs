import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import telegram as _telegram_models  # noqa: F401
from app.models.telegram import TelegramChat, TelegramMessage
from app.models.user import User
from app.services.telegram import _reaction_refresh_at, get_telegram_chat_detail, refresh_telegram_reactions
from app.tg import _reaction_summary, _store_reactions


def reaction(emoji, count=1):
    return SimpleNamespace(reaction=SimpleNamespace(emoticon=emoji), count=count)


class TelegramReactionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db = Session(self.engine)
        self.admin = User(email="admin@local.test", full_name="Admin", role="admin", password_hash="unused")
        self.teacher = User(email="teacher@local.test", full_name="Teacher", role="teacher", password_hash="unused")
        self.chat = TelegramChat(telegram_chat_id=12345, title="Student", chat_type="private")
        self.message = TelegramMessage(
            chat=self.chat, telegram_message_id=42, sender_name="Student", body="Hello", direction="inbound"
        )
        self.db.add_all([self.admin, self.teacher, self.message])
        self.db.commit()
        _reaction_refresh_at.clear()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        _reaction_refresh_at.clear()

    def test_summary_merges_standard_and_unrendered_custom_reactions(self):
        custom = SimpleNamespace(reaction=SimpleNamespace(document_id=100), count=2)
        paid = SimpleNamespace(reaction=type("ReactionPaid", (), {})(), count=1)
        actual = _reaction_summary(SimpleNamespace(results=[reaction("👍", 2), reaction("👍", 1), custom, paid]))
        self.assertEqual(actual, [
            {"emoji": "👍", "count": 3},
            {"emoji": "✨", "count": 2},
            {"emoji": "⭐", "count": 1},
        ])

    def test_raw_update_stores_and_removes_reactions_for_exact_message(self):
        other = TelegramMessage(
            chat=self.chat, telegram_message_id=43, sender_name="Student", body="Other", direction="inbound"
        )
        self.db.add(other)
        self.db.commit()
        with patch("app.tg.SessionLocal", self.session_factory):
            _store_reactions(12345, 42, SimpleNamespace(results=[reaction("❤️", 2)]))
            _store_reactions(99999, 43, SimpleNamespace(results=[reaction("👀")]))
        self.db.expire_all()
        self.assertEqual(json.loads(self.message.reactions_json), [{"emoji": "❤️", "count": 2}])
        self.assertIsNone(other.reactions_json)
        self.assertEqual(
            get_telegram_chat_detail(self.db, self.admin, self.chat.id)["messages"][0]["reactions"],
            [{"emoji": "❤️", "count": 2}],
        )
        with patch("app.tg.SessionLocal", self.session_factory):
            _store_reactions(12345, 42, SimpleNamespace(results=[]))
        self.db.expire_all()
        self.assertEqual(get_telegram_chat_detail(self.db, self.admin, self.chat.id)["messages"][0]["reactions"], [])

    def test_refresh_reconciles_telegram_state_and_throttles_polling(self):
        remote = SimpleNamespace(id=42, reactions=SimpleNamespace(results=[reaction("🔥", 3)]))
        client = SimpleNamespace(
            is_connected=lambda: True,
            get_input_entity=AsyncMock(return_value="peer"),
            get_messages=AsyncMock(return_value=[remote]),
        )
        with patch("app.tg.mtproto_client", client), patch("app.tg._mtproto_authorized", True):
            asyncio.run(refresh_telegram_reactions(self.db, self.admin, self.chat.id))
            self.assertEqual(json.loads(self.message.reactions_json), [{"emoji": "🔥", "count": 3}])
            asyncio.run(refresh_telegram_reactions(self.db, self.admin, self.chat.id))
            self.assertEqual(client.get_messages.await_count, 1)
            _reaction_refresh_at.clear()
            remote.reactions = None
            asyncio.run(refresh_telegram_reactions(self.db, self.admin, self.chat.id))
            self.assertEqual(json.loads(self.message.reactions_json), [])

    def test_teacher_without_assignment_cannot_refresh_other_chats(self):
        client = SimpleNamespace(is_connected=lambda: True, get_messages=AsyncMock())
        with patch("app.tg.mtproto_client", client), patch("app.tg._mtproto_authorized", True):
            with self.assertRaises(HTTPException) as denied:
                asyncio.run(refresh_telegram_reactions(self.db, self.teacher, self.chat.id))
        self.assertEqual(denied.exception.status_code, 403)
        client.get_messages.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
