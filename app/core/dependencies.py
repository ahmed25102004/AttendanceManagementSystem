from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token_safely
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    username = decode_token_safely(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز المصادقة غير صالح.")

    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="المستخدم غير موجود أو غير نشط.")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="صلاحية المدير مطلوبة.")
    return current_user


def get_employee_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role == "admin":
        return current_user
    if current_user.role != "employee" or not current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="صلاحية الموظف مطلوبة.")
    return current_user
