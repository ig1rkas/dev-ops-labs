"""One-time interactive login for the Telegram MTProto account.

Run this locally with ``scripts/telegram-login.cmd``. The phone number, login
code and optional two-factor password are entered in the terminal and are not
stored in the project or sent to the API.
"""

import asyncio
from pathlib import Path

from app.core.config import settings

try:
    from telethon import TelegramClient
except ImportError as exc:  # pragma: no cover - dependency is in production image
    raise SystemExit("Telethon is not installed; rebuild the app image first.") from exc


async def _login() -> None:
    if not settings.telegram_api_id or not (settings.telegram_api_hash or "").strip():
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in src/backend/.env first.")

    session_path = Path(settings.telegram_session_path).expanduser()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    phone = (settings.telegram_phone or "").strip()
    if not phone:
        phone = input("Telegram phone number (international format, e.g. +79991234567): ").strip()
    if not phone:
        raise SystemExit("A phone number is required.")

    client = TelegramClient(str(session_path), settings.telegram_api_id, settings.telegram_api_hash)
    try:
        await client.start(phone=phone)
        me = await client.get_me()
        name = " ".join(part for part in (getattr(me, "first_name", None), getattr(me, "last_name", None)) if part)
        print(f"Telegram login complete: {name or getattr(me, 'username', None) or me.id} (id={me.id})")
        print(f"Session saved to {session_path}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(_login())
