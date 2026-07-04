from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService




router = APIRouter()
auth_service = AuthService()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token = auth_service.authenticate(db, payload)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user=Depends(get_current_user)):
    return current_user


