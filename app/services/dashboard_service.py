from datetime import date

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.schemas.report import DashboardSummary


class DashboardService:
    def get_summary(self, db: Session) -> DashboardSummary:
        today = date.today()
        total_employees = db.query(Employee).filter(Employee.is_active.is_(True)).count()
        present_today = db.query(AttendanceRecord).filter(AttendanceRecord.attendance_date == today).count()
        late_employees = db.query(AttendanceRecord).filter(
            AttendanceRecord.attendance_date == today, AttendanceRecord.is_late.is_(True)
        ).count()
        absent_today = max(total_employees - present_today, 0)
        attendance_rate = round((present_today / total_employees) * 100, 2) if total_employees else 0.0

        return DashboardSummary(
            total_employees=total_employees,
            present_today=present_today,
            absent_today=absent_today,
            late_employees=late_employees,
            attendance_rate=attendance_rate,
        )
