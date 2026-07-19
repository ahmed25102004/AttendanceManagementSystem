from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token_safely
from app.models.user import User
from app.models.branch import Branch


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    db = SessionLocal()
    try:
        try:
            yield db
        finally:
            db.close()
    finally:
        db.close()


def get_current_user(db: Session = Depends(get_db)) -> User:
    # Always return admin, no auth checks
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        return user
    # If admin doesn't exist, return first active user
    user = db.query(User).filter(User.is_active.is_(True)).first()
    if user:
        return user
    # If no users found, create a dummy user? No, just return error (shouldn't happen)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="لا يوجد مستخدم في النظام")


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
    # Always allow, no checks
    return current_user


def get_current_branch_id(x_branch_id: str | None = Header(None), current_user: User = Depends(get_current_user)) -> int | None:
    # If user is branch manager, return their branch_id
    if current_user.role == "branch_manager" and current_user.branch_id:
        return current_user.branch_id
    # Otherwise, use header or None
    if x_branch_id:
        try:
            return int(x_branch_id)
        except ValueError:
            return None
    return None


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
