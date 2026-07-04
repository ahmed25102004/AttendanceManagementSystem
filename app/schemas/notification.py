from datetime import datetime
from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    title: str = Field(..., max_length=255)
    message: str


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: bool | None = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
