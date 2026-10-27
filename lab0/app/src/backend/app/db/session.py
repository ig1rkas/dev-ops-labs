from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The application runs on a small VPS. A bounded pool prevents a burst of
# polling requests from opening many PostgreSQL connections and consuming all
# available memory. Requests above this capacity fail fast instead of piling up.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=4,
    max_overflow=2,
    pool_timeout=10,
    pool_recycle=1_800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
