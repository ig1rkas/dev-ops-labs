import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_token import AuthToken
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.schemas.admin import ChangePasswordRequest

HASH_ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 210_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return f"{HASH_ALGORITHM}${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except ValueError:
        return False


def create_auth_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(40)
    db.add(AuthToken(token=token, user_id=user.id))
    db.commit()
    return token


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register_user(db: Session, payload: UserCreate) -> tuple[User, str]:
    if payload.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Администратор создается только через настройки проекта")
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже существует")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_auth_token(db, user)
    return user, token


def login_user(db: Session, payload: UserLogin) -> tuple[User, str]:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if payload.role is not None and user.role != payload.role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Для этого аккаунта выбрана другая роль")

    token = create_auth_token(db, user)
    return user, token


def get_user_by_token(db: Session, token: str) -> User | None:
    auth_token = db.scalar(select(AuthToken).where(AuthToken.token == token))
    if auth_token is None:
        return None
    return db.get(User, auth_token.user_id)


def change_user_password(db: Session, user: User, payload: ChangePasswordRequest) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Сменить пароль этим способом может только преподаватель")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текущий пароль указан неверно")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Новый пароль должен отличаться от текущего")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
