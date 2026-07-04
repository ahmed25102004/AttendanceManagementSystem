from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_employees: int
    present_today: int
    absent_today: int
    late_employees: int
    attendance_rate: float


class ReportRow(BaseModel):
    employee_code: str
    employee_name: str
    department: str | None
    job_title: str
    attendance_date: str
    check_in_time: str | None
    check_out_time: str | None
    working_hours: float
    status: str
    is_late: bool
