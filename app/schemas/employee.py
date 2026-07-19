from __future__ import annotations
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmployeeWriteBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    employee_code: str = Field(min_length=1, max_length=30)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    job_title: str = Field(min_length=2, max_length=100)
    hire_date: date
    department_id: int | None = None
    branch_id: int | None = None
    employment_type: str = "full_time"
    shift_id: int | None = None
    weekly_rest_day: str | None = Field(default=None, max_length=20)


class EmployeeCreate(EmployeeWriteBase):
    role: Literal["admin", "employee"] = "employee"


class EmployeeUpdate(EmployeeWriteBase):
    role: Literal["admin", "employee"] = "employee"


class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    role: str = "employee"
    employee_code: str
    phone: str | None = None
    address: str | None = None
    job_title: str
    hire_date: date
    first_name: str
    last_name: str
    department_id: int | None = None
    branch_id: int | None = None
    employment_type: str = "full_time"
    shift_id: int | None = None
    weekly_rest_day: str | None = None
    shift_name: str | None = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class EmployeeProfileResponse(EmployeeResponse):
    branch_name: str | None = None
    department_name: str | None = None
    shift_name: str | None = None
    face_enrolled: bool
    is_active: bool


class AttendanceLogEntry(BaseModel):
    id: int
    check_time: datetime
    attendance_type: str | None = None
    verify_type: str | None = None
    device_name: str | None = None
    branch_name: str | None = None
    
    class Config:
        from_attributes = True


class EmployeeStatsResponse(BaseModel):
    total_hours: float
    overtime_hours: float
    attendance_rate: float
    present_days: int
    absent_days: int
    late_days: int
    early_leave_days: int


class EmployeeShiftScheduleEntry(BaseModel):
    day_of_week: str = Field(min_length=3, max_length=20)
    shift_type: str = Field(min_length=2, max_length=50)
    shift_id: int | None = None
    shift_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    grace_period_minutes: int | None = None


class EmployeeShiftScheduleUpdate(BaseModel):
    shift_id: int | None = None
    weekly_rest_day: str | None = Field(default=None, max_length=20)
    schedules: list[EmployeeShiftScheduleEntry] = Field(default_factory=list)


class EmployeeShiftScheduleResponse(BaseModel):
    employee_id: int
    shift_id: int | None = None
    shift_name: str | None = None
    weekly_rest_day: str | None = None
    schedules: list[EmployeeShiftScheduleEntry]
