from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class AttendanceLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    employee_id: Optional[int] = None
    branch_id: int
    device_id: int
    employee_code: str
    check_time: datetime
    attendance_type: Optional[str] = None
    verify_type: Optional[str] = None
    source: str
    raw_data: Optional[Any] = None
    record_id: Optional[str] = None
    created_at: datetime
    # Additional fields for display
    employee_name: Optional[str] = None
    device_name: Optional[str] = None
    branch_name: Optional[str] = None
