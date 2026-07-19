from datetime import date, datetime, time

from pydantic import BaseModel, Field


class AttendanceCheckIn(BaseModel):
    employee_id: int
    attendance_date: date | None = None
    check_in_time: datetime | None = None
    source_type: str = Field(default="manual", max_length=30)
    verification_data: dict | None = None


class AttendanceCheckOut(BaseModel):
    employee_id: int
    attendance_date: date | None = None
    check_out_time: datetime | None = None
    verification_data: dict | None = None


class AttendanceManualUpdate(BaseModel):
    employee_id: int
    attendance_date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    source_type: str = Field(default="manual", max_length=30)
    notes: str | None = None


class SelfAttendanceRequest(BaseModel):
    attendance_date: date | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=5000)


class FaceDescriptorPayload(BaseModel):
    descriptor: list[float] = Field(min_length=128, max_length=128)


class FaceRegistrationRequest(BaseModel):
    descriptors: list[list[float]] = Field(min_length=1, max_length=5)


class FaceRegistrationResponse(BaseModel):
    face_registered: bool
    face_registered_at: datetime | None = None
    sample_count: int


class FaceAttendanceRequest(BaseModel):
    descriptor: list[float] = Field(min_length=128, max_length=128)
    attendance_date: date | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=5000)


class FacePortalStatusResponse(BaseModel):
    face_registered: bool
    face_registered_at: datetime | None = None
    face_verification_enabled: bool
    face_match_threshold: float
    check_in_open_time: time
    check_in_close_time: time
    check_out_open_time: time
    check_out_close_time: time


class FaceScanResponse(BaseModel):
    matched: bool
    action: str
    message: str
    confidence: float = Field(ge=0, le=1)
    distance: float = Field(ge=0)
    record: "AttendanceResponse | None" = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    attendance_date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    working_hours: float
    shift_category: str | None = None
    shift_units: float = 0
    overtime_hours: float = 0
    shift_deficit_hours: float = 0
    is_late: bool
    late_minutes: int = 0
    status: str
    source_type: str
    is_rest_day: bool = False
    worked_on_rest_day: bool = False

    class Config:
        from_attributes = True
