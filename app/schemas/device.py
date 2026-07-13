from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_name: str = Field(min_length=2, max_length=100)
    device_code: str = Field(min_length=1, max_length=50)
    serial_number: str | None = Field(default=None, max_length=100)
    branch_id: int
    ip_address: str | None = Field(default=None, max_length=45)
    port: int | None = None
    protocol: Literal["ADMS", "TCP-IP"] = "ADMS"
    firmware_version: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class DeviceUpdate(BaseModel):
    device_name: str | None = Field(default=None, min_length=2, max_length=100)
    device_code: str | None = Field(default=None, min_length=1, max_length=50)
    serial_number: str | None = Field(default=None, max_length=100)
    branch_id: int | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    port: int | None = None
    protocol: Literal["ADMS", "TCP-IP"] | None = None
    firmware_version: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class DeviceResponse(BaseModel):
    id: int
    device_name: str
    device_code: str
    serial_number: str | None = None
    branch_id: int
    ip_address: str | None = None
    port: int | None = None
    protocol: str
    firmware_version: str | None = None
    status: str
    last_sync: datetime | None = None
    last_seen: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    log_count: int | None = None

    class Config:
        from_attributes = True


class DeviceTestResponse(BaseModel):
    success: bool
    message: str
