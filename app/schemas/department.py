from pydantic import BaseModel, Field
from datetime import time


class DepartmentCreate(BaseModel):
    branch_id: int | None = Field(default=None)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    attendance_policy: str = Field(default="default", min_length=2, max_length=50)
    is_active: bool = Field(default=True)
    
    # Unified department settings (for doctors, reception, and workers)
    shift_start_time: time = Field(default="08:00:00")
    shift_end_time: time = Field(default="15:00:00")
    shift_hours: int = Field(default=7)
    late_start_time: time = Field(default="08:30:00")
    attendance_end_time: time = Field(default="11:00:00")
    overtime_enabled: bool = Field(default=True)
    overtime_start_time: time = Field(default="15:00:00")
    evening_shift_start_time: time | None = None
    evening_shift_end_time: time | None = None
    evening_shift_hours: int | None = None
    evening_shift_late_start_time: time | None = None
    
    # Backward compatibility
    half_shift_start_time: time = Field(default="08:00:00")
    half_shift_end_time: time = Field(default="15:00:00")
    half_shift_hours: int = Field(default=7)
    full_shift_start_time: time = Field(default="08:00:00")
    full_shift_end_time: time = Field(default="22:00:00")
    full_shift_hours: int = Field(default=14)
    grace_period_minutes: int = Field(default=30)


class DepartmentUpdate(BaseModel):
    branch_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    attendance_policy: str | None = Field(default=None, min_length=2, max_length=50)
    is_active: bool | None = None
    
    # Unified department settings (for doctors, reception, and workers)
    shift_start_time: time | None = None
    shift_end_time: time | None = None
    shift_hours: int | None = None
    late_start_time: time | None = None
    attendance_end_time: time | None = None
    overtime_enabled: bool | None = None
    overtime_start_time: time | None = None
    evening_shift_start_time: time | None = None
    evening_shift_end_time: time | None = None
    evening_shift_hours: int | None = None
    evening_shift_late_start_time: time | None = None
    
    # Backward compatibility
    half_shift_start_time: time | None = None
    half_shift_end_time: time | None = None
    half_shift_hours: int | None = None
    full_shift_start_time: time | None = None
    full_shift_end_time: time | None = None
    full_shift_hours: int | None = None
    overtime_start_time: time | None = None
    grace_period_minutes: int | None = None


class DepartmentResponse(DepartmentCreate):
    id: int

    class Config:
        from_attributes = True
