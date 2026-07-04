from datetime import date, datetime
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    assigned_to: int
    priority: str = "medium"
    due_date: date | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: int | None = None
    priority: str | None = None
    due_date: date | None = None
    status: str | None = None


class TaskResponse(TaskBase):
    id: int
    created_by: int
    status: str
    created_at: datetime
    updated_at: datetime
    assigned_to_name: str | None = None
    created_by_name: str | None = None
    
    class Config:
        from_attributes = True
