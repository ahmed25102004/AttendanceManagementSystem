from pydantic import BaseModel, Field, field_validator


def normalize_time(value: str | None) -> str | None:
    if not value:
        return value
    parts = value.split(":")
    if len(parts) == 2:
        return f"{value}:00"
    return value


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    check_in_open_time: str = "08:00:00"
    check_in_close_time: str = "11:00:00"
    check_out_open_time: str = "16:00:00"
    check_out_close_time: str = "22:00:00"
    allowed_late_minutes: int = 15

    _normalize_times = field_validator(
        "check_in_open_time",
        "check_in_close_time",
        "check_out_open_time",
        "check_out_close_time",
        mode="before"
    )(normalize_time)


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    check_in_open_time: str | None = None
    check_in_close_time: str | None = None
    check_out_open_time: str | None = None
    check_out_close_time: str | None = None
    allowed_late_minutes: int | None = None

    _normalize_times = field_validator(
        "check_in_open_time",
        "check_in_close_time",
        "check_out_open_time",
        "check_out_close_time",
        mode="before"
    )(normalize_time)


class BranchResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool
    check_in_open_time: str
    check_in_close_time: str
    check_out_open_time: str
    check_out_close_time: str
    allowed_late_minutes: int

    class Config:
        from_attributes = True
