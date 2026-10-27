from contextlib import asynccontextmanager
from pathlib import Path
import os

from sqlalchemy import text
from fastapi.responses import JSONResponse

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.base import Base
from app.db.schema import ensure_user_telegram_columns
from app.db.session import SessionLocal, engine
from app.models import auth_token, chat, course, learning, student_dashboard, subject, teacher, teacher_application, teacher_subject, telegram, user  # noqa: F401
from app.services.admin import ensure_admin_account, ensure_teacher_accounts, ensure_test_teacher_account
from app.services.catalog import ensure_teacher_subject_links, seed_catalog
from app.services.courses import seed_courses
from app.tg import start_telegram_polling, stop_telegram_polling


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        ensure_user_telegram_columns(engine)
        with SessionLocal() as db:
            seed_courses(db)
            seed_catalog(db)
            ensure_teacher_subject_links(db)
            ensure_admin_account(db)
            if settings.seed_public_teacher_accounts:
                ensure_teacher_accounts(db)
            if settings.seed_demo_accounts:
                ensure_test_teacher_account(db)
    await start_telegram_polling()
    yield
    await stop_telegram_polling()


app = FastAPI(title=settings.project_name, version="0.1.0", lifespan=lifespan)

@app.middleware("http")
async def identify_instance(request, call_next):
    response = await call_next(request)
    response.headers["X-Instance-ID"] = os.getenv("INSTANCE_ID", "backend")
    return response


@app.get("/api/readiness", include_in_schema=False)
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "instance": os.getenv("INSTANCE_ID", "backend")}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "database unavailable"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        return FileResponse(STATIC_DIR / "favicon.svg")


    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested_file = STATIC_DIR / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(INDEX_FILE)
