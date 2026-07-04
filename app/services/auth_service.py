from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import security_manager
from app.models.employee import Employee
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.employee_service import EmployeeService


class AuthService:
    def _find_user(self, db: Session, username: str) -> User | None:
        normalized_username = username.strip().lower()
        user = (
            db.query(User)
            .filter(func.lower(User.username) == normalized_username, User.is_active.is_(True))
            .first()
        )
        return user

    def authenticate(self, db: Session, payload: LoginRequest) -> str:
        user = self._find_user(db, payload.username)
        if not user or not security_manager.verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة.",
            )
        return security_manager.create_access_token(subject=user.username)

