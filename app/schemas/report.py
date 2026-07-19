from pydantic import BaseModel


class WeeklyAttendanceData(BaseModel):
    labels: list[str]
    present: list[int]
    late: list[int]


class DashboardSummary(BaseModel):
    total_employees: int
    present_today: int
    absent_today: int
    late_employees: int
    attendance_rate: float
    weekly_data: WeeklyAttendanceData


class ReportRow(BaseModel):
    employee_code: str
    employee_name: str
    department: str | None
    job_title: str
    attendance_date: str
    row_kind: str = "daily"
    shift_name: str | None = None
    shift_type: str | None = None
    shift_start_time: str | None = None
    shift_end_time: str | None = None
    check_in_time: str | None
    check_out_time: str | None
    working_hours: float
    overtime_hours: float = 0
    shift_deficit_hours: float = 0
    status: str
    is_late: bool
    late_minutes: int = 0
    worked_on_rest_day: bool = False
    absent_days_count: int = 0
    weekly_rest_days_count: int = 0
    worked_on_rest_days_count: int = 0
    full_shift_count: int = 0
    half_shift_count: int = 0
    total_shift_units: float = 0
    total_late_minutes: int = 0
    total_overtime_hours: float = 0
