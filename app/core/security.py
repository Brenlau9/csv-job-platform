from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from secrets import token_bytes

import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()
PBKDF2_ITERATIONS = 100_000
PBKDF2_ALGORITHM = "sha256"


def _encode_bytes(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("utf-8")


def _decode_bytes(value: str) -> bytes:
    return urlsafe_b64decode(value.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = token_bytes(16)
    password_hash = pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_encode_bytes(salt)}${_encode_bytes(password_hash)}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    candidate_hash = pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        plain_password.encode("utf-8"),
        _decode_bytes(salt),
        int(iterations),
    )
    return compare_digest(candidate_hash, _decode_bytes(expected_hash))


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(subject: str) -> str:
    expire_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    payload = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
