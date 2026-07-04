from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse
from app.services.notification_service import NotificationService


router = APIRouter()
notification_service = NotificationService()


@router.get("", response_model=list[NotificationResponse])
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return notification_service.list_for_user(db, current_user.id)


@router.post("", response_model=NotificationResponse, dependencies=[Depends(get_current_user)])
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db)
):
    return notification_service.create(db, payload)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return notification_service.get(db, notification_id, current_user.id)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return notification_service.mark_as_read(db, notification_id, current_user.id)


@router.put("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    notification_service.mark_all_as_read(db, current_user.id)
    return {"message": "تم تعليم جميع الإشعارات كمقروءة"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    notification_service.delete(db, notification_id, current_user.id)
    return {"message": "تم حذف الإشعار"}
