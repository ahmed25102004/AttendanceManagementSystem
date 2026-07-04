from datetime import date, datetime
from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field


class LeaveType(str, Enum):
    SICK = "sick"
    ANNUAL = "annual"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveBase(BaseModel):
    employee_id: int
    type: LeaveType
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveCreate(LeaveBase):
    pass


class LeaveUpdate(BaseModel):
    type: LeaveType | None = None
    start_date: date | None = None
    end_date: date | None = None
    reason: str | None = None
    status: LeaveStatus | None = None


class LeaveResponse(LeaveBase):
    id: int
    status: LeaveStatus
    created_at: datetime
    updated_at: datetime
    employee_name: str | None = None

    class Config:
        from_attributes = True
