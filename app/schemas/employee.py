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
