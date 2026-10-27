from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "idioma API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://idioma:idioma@localhost:5432/idioma"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_create_tables: bool = True
    admin_email: str = "admin@idioma.school"
    admin_password: str = "admin123"
    admin_name: str = "Администратор idioma"
    test_teacher_email: str = "teacher-test@idioma.school"
    test_teacher_password: str = "teacher123"
    test_teacher_name: str = "Тестовый преподаватель"
    # Local development gets ready-made accounts. Production turns this off so
    # no account with a predictable password is created on startup.
    seed_demo_accounts: bool = True
    # Public catalog cards need real teacher accounts so an administrator can
    # manage them. Deleted profiles remain disabled and are not recreated.
    seed_public_teacher_accounts: bool = True
    telegram_bot_token: str | None = None
    telegram_polling_enabled: bool = True
    # MTProto settings for a user-authorized Telegram client. The API id/hash
    # identify the client application; the session is authorized separately
    # with the phone number of the account that should send messages.
    telegram_mtproto_enabled: bool = False
    telegram_api_id: int = 0
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    telegram_session_path: str = "/data/telegram/idioma.session"
    # 0 means import the complete available history in the background.
    telegram_history_limit: int = 0
    telegram_sync_dialogs: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
