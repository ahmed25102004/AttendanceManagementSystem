from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmployeeWriteBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    job_title: str = Field(min_length=2, max_length=100)
    hire_date: date
    department_id: int | None = None
    employment_type: str = "full_time"


class EmployeeCreate(EmployeeWriteBase):
    role: Literal["admin", "employee"] = "employee"


class EmployeeUpdate(EmployeeWriteBase):
    role: Literal["admin", "employee"] = "employee"


class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    role: str = "employee"
    phone: str | None = None
    address: str | None = None
    job_title: str
    hire_date: date
    first_name: str
    last_name: str
    department_id: int | None = None
    employment_type: str = "full_time"
    
    class Config:
        from_attributes = True
