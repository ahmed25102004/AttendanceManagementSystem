from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token_safely
from app.models.user import User
from app.models.branch import Branch


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        try:
            yield db
        finally:
            db.close()
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="يجب تسجيل الدخول أولاً.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_token_safely(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز الدخول غير صالح أو منتهي الصلاحية.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="المستخدم غير موجود أو غير نشط.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    # Only allow admin
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك صلاحية للوصول")
    return current_user


def get_branch_manager_or_admin(current_user: User = Depends(get_current_user)) -> User:
    # Allow admin or branch_manager
    if current_user.role not in ["admin", "branch_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك صلاحية للوصول")
    return current_user


def get_employee_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def get_current_branch_id(x_branch_id: str | None = Header(None), current_user: User = Depends(get_current_user)) -> int | None:
    if current_user.role == "branch_manager" and current_user.branch_id:
        return current_user.branch_id
    if x_branch_id:
        try:
            return int(x_branch_id)
        except ValueError:
            return None
    return None


def resolve_branch_scope(current_user: User, branch_id: int | None, include_all: bool = False) -> int | None:
    if current_user.role == "admin":
        return None if include_all else branch_id
    if current_user.role == "branch_manager":
        return current_user.branch_id
    return branch_id


def get_required_branch_id(
    x_branch_id: int | None = Depends(get_current_branch_id),
    db: Session = Depends(get_db)
) -> int:
    if not x_branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لم يتم تحديد الفرع.")
    # Verify branch exists
    branch = db.query(Branch).filter(Branch.id == x_branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفرع غير موجود.")
    if not branch.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="الفرع غير نشط.")
    return x_branch_id
