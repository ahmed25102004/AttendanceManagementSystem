from datetime import time

from pydantic import BaseModel, Field


class CompanySettingUpdate(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    work_start_time: time
    work_end_time: time
    weekend_days: list[str]
    late_grace_minutes: int = Field(ge=0, le=240)
    workplace_latitude: float | None = Field(default=None, ge=-90, le=90)
    workplace_longitude: float | None = Field(default=None, ge=-180, le=180)
    workplace_radius_meters: int = Field(default=150, ge=20, le=5000)
    allowed_ip_ranges: list[str] = Field(default_factory=list)
    enforce_geofence: bool = False
    enforce_ip_check: bool = False
    face_match_threshold: float = Field(default=0.45, ge=0.1, le=1.5)
    check_in_open_time: time = time(7, 30)
    check_in_close_time: time = time(10, 0)
    check_out_open_time: time = time(16, 0)
    check_out_close_time: time = time(19, 0)
    auto_backup_enabled: bool = False
    auto_backup_time: time = time(2, 0)
    auto_backup_retention_days: int = Field(default=30, ge=1, le=365)
    zkteco_enabled: bool = False
    zkteco_ip: str | None = Field(default="192.168.1.201", max_length=50)
    zkteco_port: int = Field(default=4370, ge=1, le=65535)
    zkteco_password: str | None = Field(default="", max_length=100)
    zkteco_auto_sync_enabled: bool = False
    zkteco_auto_sync_interval_minutes: int = Field(default=30, ge=1, le=1440)


class CompanySettingResponse(BaseModel):
    id: int
    company_name: str
    work_start_time: time
    work_end_time: time
    weekend_days: list[str]
    late_grace_minutes: int
    workplace_latitude: float | None
    workplace_longitude: float | None
    workplace_radius_meters: int
    allowed_ip_ranges: list[str]
    enforce_geofence: bool
    enforce_ip_check: bool
    face_match_threshold: float
    check_in_open_time: time
    check_in_close_time: time
    check_out_open_time: time
    check_out_close_time: time
    auto_backup_enabled: bool
    auto_backup_time: time
    auto_backup_retention_days: int
    zkteco_enabled: bool
    zkteco_ip: str
    zkteco_port: int
    zkteco_password: str
    zkteco_auto_sync_enabled: bool
    zkteco_auto_sync_interval_minutes: int
