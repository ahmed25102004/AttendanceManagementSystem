from datetime import time
from pydantic import BaseModel, Field


class ShiftBase(BaseModel):
    name: str = Field(..., max_length=100)
    start_time: time
    end_time: time
    grace_period_minutes: int = 15
    is_active: bool = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    name: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    grace_period_minutes: int | None = None
    is_active: bool | None = None


class ShiftResponse(ShiftBase):
    id: int

    class Config:
        from_attributes = True
