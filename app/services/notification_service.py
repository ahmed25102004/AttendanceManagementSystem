from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate


class NotificationService:
    def create(self, db: Session, payload: NotificationCreate) -> Notification:
        notification = Notification(**payload.model_dump())
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    def list_for_user(self, db: Session, user_id: int) -> list[Notification]:
        return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()

    def get(self, db: Session, notification_id: int, user_id: int) -> Notification:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الإشعار غير موجود"
            )
        
        return notification

    def mark_as_read(self, db: Session, notification_id: int, user_id: int) -> Notification:
        notification = self.get(db, notification_id, user_id)
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, user_id: int) -> None:
        db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({Notification.is_read: True})
        db.commit()

    def delete(self, db: Session, notification_id: int, user_id: int) -> None:
        notification = self.get(db, notification_id, user_id)
        db.delete(notification)
        db.commit()
