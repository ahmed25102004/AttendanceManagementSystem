from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, subject: str, expires_delta: timedelta | None = None) -> str:
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
        )
        payload: dict[str, Any] = {"sub": subject, "exp": expire}
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


security_manager = SecurityManager()


def decode_token_safely(token: str) -> str | None:
    try:
        payload = security_manager.decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
